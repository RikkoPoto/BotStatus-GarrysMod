import discord
from discord.ext import commands, tasks
import os
import json
import time
import re

# ============================================================
#  PLANTILLAS — REEMPLAZA LOS CEROS CON TUS IDs REALES
# ============================================================

# 1. IDs de los roles de los rangos
ROLES_RANGO = {
    "diamond": 1519101667956625569,
    "golden":       1519101837985185792,
    "silver":     1519101736466513940
}

# 2. IDs de los roles que pueden usar el comando (Owner y Co-owner)
ROLES_AUTORIZADOS = [
    1501738614718205972, # Reemplaza por el ID del rol Owner
    1501738637178704043  # Reemplaza por el ID del rol Co-owner
]

# 3. ID del canal donde el bot avisará que expiró el rango
CANAL_NOTIFICACIONES_ID = 1519110810436370523

# ============================================================

RANKS_FILE = "ranks_data.json"

def load_ranks():
    """Carga los datos de los rangos activos."""
    if not os.path.exists(RANKS_FILE):
        return {"active_ranks": []}
    with open(RANKS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"active_ranks": []}

def save_ranks(data):
    """Guarda los rangos en el archivo JSON."""
    with open(RANKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_duration(time_str: str) -> int:
    """Convierte un string como '30d', '24h' a segundos."""
    if not time_str:
        return 0
    time_str = time_str.lower()
    match = re.match(r"^(\d+)(s|m|h|d|hrs?|mins?|dias?)$", time_str)
    if not match: return 0
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit.startswith('s'): return amount
    if unit.startswith('m'): return amount * 60
    if unit.startswith('h'): return amount * 3600
    if unit.startswith('d'): return amount * 86400
    return 0

class RanksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_expired_ranks.start()

    def cog_unload(self):
        self.check_expired_ranks.cancel()

    def is_authorized(self, member: discord.Member):
        """Revisa si el usuario tiene el rol de Owner o Co-owner."""
        for role in member.roles:
            if role.id in ROLES_AUTORIZADOS:
                return True
        return False

    @tasks.loop(minutes=1)
    async def check_expired_ranks(self):
        """Revisa cada minuto si hay rangos que deban ser retirados."""
        data = load_ranks()
        now = time.time()
        to_remove = []

        for rank_data in data.get("active_ranks", []):
            if now >= rank_data["end_time"]:
                guild = self.bot.get_guild(rank_data["guild_id"])
                if guild:
                    canal = guild.get_channel(CANAL_NOTIFICACIONES_ID)
                    miembro = guild.get_member(rank_data["user_id"])
                    role = guild.get_role(rank_data["role_id"])

                    # 1. Quitar el rol en Discord si el usuario sigue en el server
                    if miembro and role:
                        try:
                            await miembro.remove_roles(role, reason="Tiempo de rango expirado.")
                        except Exception as e:
                            print(f"[RANGOS] No se pudo quitar el rol a {miembro.name}: {e}")

                    # 2. Enviar notificación al canal etiquetando a Owner y Co-owner
                    if canal:
                        menciones = " ".join([f"<@&{role_id}>" for role_id in ROLES_AUTORIZADOS])
                        usuario_mencion = f"<@{rank_data['user_id']}>"
                        
                        mensaje = (
                            f"⚠️ {menciones} **¡Atención!**\n"
                            f"El tiempo del rango **{rank_data['role_name'].capitalize()}** del jugador {usuario_mencion} ha expirado.\n"
                            f"👉 *El rol ha sido retirado automáticamente en Discord. Por favor, retirarlo dentro del juego.*"
                        )
                        await canal.send(mensaje)
                        
                to_remove.append(rank_data)

        # 3. Borrar del JSON los que ya expiraron
        if to_remove:
            for r in to_remove:
                if r in data["active_ranks"]:
                    data["active_ranks"].remove(r)
            save_ranks(data)

    @check_expired_ranks.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="rango")
    async def cmd_rango(self, ctx, member: discord.Member, nombre_rol: str, duration: str):
        """Otorga un rango VIP temporal y suma el tiempo si ya lo tiene."""
        
        if not self.is_authorized(ctx.author):
            return await ctx.send("❌ No tienes permisos para usar este comando. Solo Owner/Co-owner pueden hacerlo.")

        rol_key = nombre_rol.lower()
        if rol_key not in ROLES_RANGO:
            return await ctx.send("❌ Rango no válido. Los rangos disponibles son: `diamond`, `golden`, `silver`.")

        segundos = parse_duration(duration)
        if segundos <= 0:
            return await ctx.send("❌ Tiempo inválido. Usa formatos como `30d`, `24h`, `15m`.")

        rol_id = ROLES_RANGO[rol_key]
        rol_obj = ctx.guild.get_role(rol_id)

        if not rol_obj:
            return await ctx.send("❌ No pude encontrar el rol en el servidor. Verifica que los IDs en la plantilla estén correctos.")

        try:
            data = load_ranks()
            active_ranks = data.setdefault("active_ranks", [])
            
            rango_existente = None
            for rank in active_ranks:
                if rank["user_id"] == member.id and rank["role_id"] == rol_id:
                    rango_existente = rank
                    break
                    
            if rango_existente:
                # Sumamos el tiempo
                if rango_existente["end_time"] > time.time():
                    rango_existente["end_time"] += segundos
                else:
                    rango_existente["end_time"] = time.time() + segundos
                
                rango_existente["assigned_by"] = ctx.author.id
                rango_existente["assigned_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_ranks(data)
                
                if rol_obj not in member.roles:
                    await member.add_roles(rol_obj, reason=f"Extensión de rango por {ctx.author.name}.")
                    
                await ctx.send(f"⏳ ✅ Se ha extendido el rango **{rol_obj.name}** de **{member.name}** sumando **{duration}** adicionales.")
            
            else:
                await member.add_roles(rol_obj, reason=f"Otorgado por {ctx.author.name} por {duration}.")
                active_ranks.append({
                    "guild_id": ctx.guild.id,
                    "user_id": member.id,
                    "role_id": rol_id,
                    "role_name": rol_key,
                    "end_time": time.time() + segundos,
                    "assigned_by": ctx.author.id,
                    "assigned_date": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                save_ranks(data)
                await ctx.send(f"💎 ✅ El usuario **{member.name}** ha recibido el rango **{rol_obj.name}** por un periodo de **{duration}**.")

        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos. Asegúrate de que el rol de mi bot esté MÁS ARRIBA en la lista que los roles Diamond/Golden/Silver.")

    @cmd_rango.error
    async def rango_error(self, ctx, error):
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("⚠️ **Uso incorrecto.** La estructura correcta es:\n`$rango @Usuario [diamond/golden/silver] [tiempo]`\n*Ejemplo:* `$rango @Xacter diamond 30d`")

    @commands.command(name="tiemporango", aliases=["inforango", "tiempo"])
    async def cmd_tiemporango(self, ctx, member: discord.Member = None):
        """Consulta cuánto tiempo le queda a un usuario en su rango VIP."""
        if member is None:
            member = ctx.author

        data = load_ranks()
        now = time.time()
        
        user_ranks = [r for r in data.get("active_ranks", []) if r["user_id"] == member.id]
        
        if not user_ranks:
            return await ctx.send(f"❌ **{member.name}** no tiene ningún rango VIP activo en este momento.")
            
        mensaje = f"📊 **Información de Rangos VIP para {member.name}**\n\n"
        
        for rank in user_ranks:
            remaining = rank["end_time"] - now
            if remaining <= 0:
                continue
                
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            minutes = int((remaining % 3600) // 60)
            
            time_str = []
            if days > 0: time_str.append(f"**{days}** días")
            if hours > 0: time_str.append(f"**{hours}** horas")
            if minutes > 0: time_str.append(f"**{minutes}** minutos")
            
            if not time_str: 
                tiempo_restante = "Menos de un minuto"
            else:
                tiempo_restante = ", ".join(time_str)
                
            rol_nombre = rank["role_name"].capitalize()
            mensaje += f"💎 **Rango:** {rol_nombre}\n⏳ **Tiempo restante:** {tiempo_restante}\n\n"
            
        await ctx.send(mensaje)

async def setup(bot):
    await bot.add_cog(RanksCog(bot))