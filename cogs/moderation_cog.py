import discord
from discord.ext import commands, tasks
import asyncio
import re
import json
import os
import time

DATA_FILE = "mod_data.json"

def load_data():
    """Carga los datos del archivo JSON. Si no existe, crea la estructura base."""
    if not os.path.exists(DATA_FILE):
        return {"tempbans": [], "history": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"tempbans": [], "history": []}

def save_data(data):
    """Guarda los datos en el archivo JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_duration(time_str: str) -> int:
    """Convierte un string como '24h', '10m', '1d' a segundos."""
    if not time_str:
        return 0
        
    time_str = time_str.lower()
    # Busca un número seguido de una unidad de tiempo
    match = re.match(r"^(\d+)(s|m|h|d|hrs?|mins?|dias?)$", time_str)
    if not match:
        return 0
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit.startswith('s'): return amount
    if unit.startswith('m'): return amount * 60
    if unit.startswith('h'): return amount * 3600
    if unit.startswith('d'): return amount * 86400
    return 0

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Iniciamos el ciclo que revisará los desbaneos pendientes
        self.check_tempbans.start()

    def cog_unload(self):
        # Cancelamos el ciclo si el bot se apaga
        self.check_tempbans.cancel()

    @tasks.loop(minutes=1)
    async def check_tempbans(self):
        """Revisa cada minuto si hay jugadores que deben ser desbaneados."""
        data = load_data()
        now = time.time()
        to_remove = []
        
        for tb in data.get("tempbans", []):
            if now >= tb["unban_time"]:
                guild = self.bot.get_guild(tb["guild_id"])
                if guild:
                    try:
                        user = await self.bot.fetch_user(tb["user_id"])
                        await guild.unban(user, reason="Tiempo de ban temporal expirado automáticamente.")
                    except:
                        pass # Si hay error (ej. fue desbaneado a mano), simplemente lo ignoramos
                to_remove.append(tb)
                
        # Guardamos el JSON si hubo jugadores desbaneados
        if to_remove:
            for tb in to_remove:
                if tb in data["tempbans"]:
                    data["tempbans"].remove(tb)
            save_data(data)

    @check_tempbans.before_loop
    async def before_check(self):
        """Espera a que el bot esté listo antes de revisar bans."""
        await self.bot.wait_until_ready()

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True) # Requiere permisos de kickear
    async def cmd_kick(self, ctx, member: discord.Member, *, reason: str = "Sin motivo"):
        """Kickea a un usuario del servidor de Discord."""
        if member == ctx.author:
            return await ctx.send("❌ No puedes kickearte a ti mismo.")
            
        try:
            await member.kick(reason=reason)
            
            # Guardamos el historial del kick en el JSON
            data = load_data()
            data.setdefault("history", []).append({
                "action": "kick",
                "user": str(member),
                "user_id": member.id,
                "reason": reason,
                "date": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            save_data(data)

            await ctx.send(f"👢 ✅ **{member.name}** ha sido kickeado.\n📝 **Motivo:** {reason}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos suficientes para kickear a ese usuario (¿Tiene un rol superior al mío?).")

    @cmd_kick.error
    async def kick_error(self, ctx, error):
        """Maneja los errores cuando se usa mal el comando $kick"""
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("⚠️ **Uso incorrecto.** La estructura correcta es:\n`$kick @Usuario [motivo opcional]`\n*Ejemplo:* `$kick @Usuario Romper las reglas`")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ No tienes permisos para usar este comando.")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True) # Requiere permisos de banear
    async def cmd_ban(self, ctx, member: discord.Member, duration: str = None, *, reason: str = "Sin motivo"):
        """
        Banea a un usuario. 
        Uso: $ban @Usuario [tiempo] [motivo]
        Ejemplos: $ban @Usuario 24h Spam | $ban @Usuario Toxicidad (Ban permanente)
        """
        if member == ctx.author:
            return await ctx.send("❌ No puedes banearte a ti mismo.")

        # Calculamos los segundos basados en la duración
        seconds = parse_duration(duration) if duration else 0
        
        # Flexibilidad: Si el usuario escribe "$ban @User Motivo" (sin tiempo),
        # 'duration' tomará la palabra "Motivo". Como no es un tiempo válido (seconds = 0),
        # lo reasignamos para que sea parte de la razón del ban y lo hacemos permanente.
        if duration and seconds == 0:
            if reason == "Sin motivo":
                reason = duration
            else:
                reason = f"{duration} {reason}"
            duration = None # Al no haber duración, es permanente

        try:
            await member.ban(reason=reason)
            
            data = load_data()
            # Guardamos historial general del ban en el JSON
            data.setdefault("history", []).append({
                "action": "ban",
                "duration": duration or "Permanente",
                "user": str(member),
                "user_id": member.id,
                "reason": reason,
                "date": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            if seconds > 0:
                # Agregamos a la lista de tempbans para ser desbaneado en el futuro
                data.setdefault("tempbans", []).append({
                    "guild_id": ctx.guild.id,
                    "user_id": member.id,
                    "unban_time": time.time() + seconds
                })
                save_data(data)
                
                await ctx.send(f"🔨 ✅ **{member.name}** ha sido baneado temporalmente por **{duration}**.\n📝 **Motivo:** {reason}")
            else:
                save_data(data)
                await ctx.send(f"🔨 ✅ **{member.name}** ha sido baneado permanentemente.\n📝 **Motivo:** {reason}")

        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos suficientes para banear a ese usuario (¿Tiene un rol superior al mío?).")

    @cmd_ban.error
    async def ban_error(self, ctx, error):
        """Maneja los errores cuando se usa mal el comando $ban"""
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("⚠️ **Uso incorrecto.** La estructura correcta es:\n`$ban @Usuario [tiempo opcional] [motivo]`\n*Ejemplos:*\n`$ban @Usuario 24h Spam` (Ban temporal)\n`$ban @Usuario Toxicidad` (Ban permanente)")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ No tienes permisos para usar este comando.")

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))