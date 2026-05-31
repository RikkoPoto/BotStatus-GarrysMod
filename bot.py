import discord
from discord.ext import commands, tasks
import a2s
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ============================================================
#  CONFIGURACIÓN — Edita estos valores
# ============================================================
SERVER_IP   = "151.242.242.197"       # Ej: "192.168.1.100" o "mi.servidor.com"
SERVER_PORT = 27015               # Puerto de tu servidor Gmod (por defecto 27015)
QUERY_PORT  = 27070               # Puerto de query (generalmente igual al de juego)

# Canal de Discord donde se enviará/actualizará el estado
STATUS_CHANNEL_ID = 1502049429752910045   # <-- Reemplaza con el ID de tu canal

# Cada cuántos segundos se actualiza el embed (mínimo 30 recomendado)
UPDATE_INTERVAL = 60

# ============================================================
#  DECORACIÓN DEL EMBED — Personaliza a tu gusto
# ============================================================
EMBED_CONFIG = {
    "color_online":  0x57F287,   # Verde cuando el server está online
    "color_offline": 0xED4245,   # Rojo cuando está offline
    "thumbnail_url": "",         # URL de imagen pequeña (esquina superior derecha). Dejar vacío para omitir.
    "image_url":     "",         # URL de imagen grande en el footer del embed. Dejar vacío para omitir.
    "footer_text":   "🕹️ Estado actualizado automáticamente",
    "footer_icon":   "",         # URL del ícono del footer. Dejar vacío para omitir.
}
# ============================================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ID del mensaje que se va a editar en vez de crear nuevos
status_message_id: int | None = None


def query_server() -> dict:
    """Consulta el servidor via protocolo Source Engine. Retorna un dict con la info."""
    address = (SERVER_IP, QUERY_PORT)
    try:
        info    = a2s.info(address, timeout=5)
        players = a2s.players(address, timeout=5)
        return {
            "online":      True,
            "name":        info.server_name,
            "map":         info.map_name,
            "players":     info.player_count,
            "max_players": info.max_players,
            "player_list": [p.name for p in players if p.name],
            "ip":          SERVER_IP,
            "port":        SERVER_PORT,
            "vac":         info.vac_enabled,
            "game":        info.game,
        }
    except Exception:
        return {"online": False}


def build_embed(data: dict) -> discord.Embed:
    """Construye el embed de Discord con los datos del servidor."""
    now = datetime.utcnow()

    if data["online"]:
        embed = discord.Embed(
            title="🟢  Servidor Online",
            color=EMBED_CONFIG["color_online"],
            timestamp=now,
        )

        embed.add_field(
            name="🏷️  Nombre Del Servidor",
            value=f"```{data['name']}```",
            inline=False,
        )
        embed.add_field(
            name="🗺️  Mapa actual",
            value=f"`{data['map']}`",
            inline=True,
        )
        embed.add_field(
            name="👥  Jugadores",
            value=f"`{data['players']} / {data['max_players']}`",
            inline=True,
        )
        embed.add_field(
            name="🔒  VAC",
            value="`Activado`" if data["vac"] else "`Desactivado`",
            inline=True,
        )
        embed.add_field(
            name="🔌  Conexión",
            value=f"```connect {data['ip']}:{data['port']}```",
            inline=False,
        )

        # Lista de jugadores (opcional, máximo 15 para no ocupar demasiado espacio)
        if data["player_list"]:
            names = data["player_list"][:15]
            display = "\n".join(f"• {n}" for n in names)
            if len(data["player_list"]) > 15:
                display += f"\n*... y {len(data['player_list']) - 15} más*"
            embed.add_field(
                name=f"📋  Jugadores conectados ({len(data['player_list'])})",
                value=display,
                inline=False,
            )
        else:
            embed.add_field(
                name="📋  Jugadores conectados",
                value="*El servidor está vacío*",
                inline=False,
            )

    else:
        embed = discord.Embed(
            title="🔴  Servidor Offline",
            description="No se pudo conectar al servidor. Puede estar caído o en mantenimiento.",
            color=EMBED_CONFIG["color_offline"],
            timestamp=now,
        )
        embed.add_field(
            name="🔌  Dirección configurada",
            value=f"```{SERVER_IP}:{SERVER_PORT}```",
            inline=False,
        )

    # Aplicar decoración
    if EMBED_CONFIG["thumbnail_url"]:
        embed.set_thumbnail(url=EMBED_CONFIG["thumbnail_url"])
    if EMBED_CONFIG["image_url"]:
        embed.set_image(url=EMBED_CONFIG["image_url"])

    footer_kwargs = {"text": EMBED_CONFIG["footer_text"]}
    if EMBED_CONFIG["footer_icon"]:
        footer_kwargs["icon_url"] = EMBED_CONFIG["footer_icon"]
    embed.set_footer(**footer_kwargs)

    return embed


@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_status():
    """Tarea periódica: edita el mensaje de estado o crea uno nuevo."""
    global status_message_id

    channel = bot.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        print(f"[ERROR] No se encontró el canal con ID {STATUS_CHANNEL_ID}")
        return

    data  = query_server()
    embed = build_embed(data)

    try:
        if status_message_id:
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            status_message_id = msg.id
            print(f"[INFO] Mensaje de estado creado. ID: {status_message_id}")
    except discord.NotFound:
        # El mensaje fue borrado — crear uno nuevo
        msg = await channel.send(embed=embed)
        status_message_id = msg.id
    except Exception as e:
        print(f"[ERROR] Al actualizar embed: {e}")

    estado = "🟢 ONLINE" if data["online"] else "🔴 OFFLINE"
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {estado} | Jugadores: {data.get('players', '—')}")


@bot.event
async def on_ready():
    print(f"✅  Bot conectado como {bot.user}")
    print(f"📡  Monitoreando {SERVER_IP}:{SERVER_PORT} cada {UPDATE_INTERVAL}s")
    update_status.start()


# Comando manual para forzar actualización
@bot.command(name="status")
async def cmd_status(ctx):
    """!status — Muestra el estado actual del servidor al instante."""
    data  = query_server()
    embed = build_embed(data)
    await ctx.send(embed=embed)


# Comando para configurar el mensaje fijo (útil al mover canales)
@bot.command(name="setstatus")
@commands.has_permissions(administrator=True)
async def cmd_setstatus(ctx):
    """!setstatus — (Admin) Crea un nuevo mensaje de estado fijo en este canal."""
    global status_message_id, STATUS_CHANNEL_ID
    STATUS_CHANNEL_ID = ctx.channel.id
    status_message_id = None
    await ctx.message.delete()
    await update_status()


bot.run(os.getenv("DISCORD_TOKEN"))
