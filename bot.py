import discord
from discord.ext import commands, tasks
import a2s
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

# ============================================================
#  CONFIGURACIÓN — Edita estos valores
# ============================================================
SERVER_IP   = "151.242.242.197"
SERVER_PORT = 27070
# Lista de puertos a intentar si el principal falla (27070, luego 27015, etc.)
PORTS_TO_TRY = [27070, 27015, 27071] 

STATUS_CHANNEL_ID = 1502049429752910045   # ID de tu canal

UPDATE_INTERVAL = 60 # Segundos entre actualizaciones


# ============================================================
#  DECORACIÓN DEL EMBED — Personaliza a tu gusto
# ============================================================
EMBED_CONFIG = {
    "color_online":  0x57F287,
    "color_offline": 0xED4245,
    "thumbnail_url": "", 
    "image_url":     "", 
    "footer_text":   "🕹️ Estado actualizado automáticamente",
    "footer_icon":   "",
}
# ============================================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ID del mensaje que se va a editar en vez de crear nuevos
status_message_id: int | None = None

async def query_server() -> dict:
    """Busca el servidor intentando varios puertos."""
    for port in PORTS_TO_TRY:
        address = (SERVER_IP, port)
        try:
            # 1. Intentar obtener la información básica (Nombre, Mapa, Jugadores online)
            info = await a2s.ainfo(address, timeout=3.0)
            
            # 2. Intentar obtener los NOMBRES de los jugadores (Suele fallar en algunos hostings)
            player_list = []
            try:
                players = await a2s.aplayers(address, timeout=2.0)
                player_list = [p.name for p in players if p.name]
            except Exception as e:
                print(f"[DEBUG] Se obtuvo info del server, pero falló la lista de jugadores en puerto {port}.")

            return {
                "online":      True,
                "name":        info.server_name,
                "map":         info.map_name,
                "players":     info.player_count,
                "max_players": info.max_players,
                "player_list": player_list,
                "ip":          SERVER_IP,
                "port":        SERVER_PORT,
                "vac":         info.vac_enabled,
                "game":        info.game,
            }
        except Exception as e:
            # Si falla este puerto, el bucle for intentará con el siguiente
            print(f"[DEBUG] Falló intento en puerto {port}: {e}")
            continue
            
    # Si probó todos los puertos y todos fallaron:
    return {"online": False}


def build_embed(data: dict) -> discord.Embed:
    """Construye el mensaje visual (Embed)"""
    now = datetime.now(ZoneInfo("America/Santiago"))

    if data["online"]:
        embed = discord.Embed(
            title="🟢  Servidor Online",
            color=EMBED_CONFIG["color_online"],
            timestamp=now,
        )

        embed.add_field(
            name="🏷️  Nombre Del Servidor", 
            value=f"```{data['name']}```",
            inline=False)
        embed.add_field(
            name="🗺️  Mapa actual", 
            value=f"`{data['map']}`",
            inline=True)
        embed.add_field(
            name="👥  Jugadores", 
            value=f"`{data['players']} / {data['max_players']}`",
            inline=True)
        embed.add_field(
            name="🔒  VAC", 
            value="`Activado`" if data["vac"] else "`Desactivado`", 
            inline=True)
        embed.add_field(
            name="🔌  Conexión", 
            value=f"```{data['ip']}:{data['port']}```", 
            inline=False)
        
# Solo mostrar lista si hay jugadores Y el servidor permitió leer sus nombres
        if data["player_list"]:
            names = data["player_list"][:15]
            display = "\n".join(f"• {n}" for n in names)
            if len(data["player_list"]) > 15:
                display += f"\n*... y {len(data['player_list']) - 15} más*"
            embed.add_field(
                name=f"📋  Jugadores conectados ({len(data['player_list'])})", 
                value=display, inline=False)
        elif data["players"] > 0:
            embed.add_field(
                name="📋  Jugadores", 
                value="*Hay jugadores, pero el servidor oculta los nombres*", 
                inline=False)
        else:
            embed.add_field(
                name="📋  Jugadores conectados", 
                value="*El servidor está vacío*", 
                inline=False)

    else:
        embed = discord.Embed(
            title="🔴  Servidor Offline",
            description="No se pudo conectar al servidor. Puede estar caído o reiniciándose.",
            color=EMBED_CONFIG["color_offline"],
            timestamp=now,
        )
        embed.add_field(
            name="🔌  Dirección", 
            value=f"```{data.get('ip', SERVER_IP)}:{data.get('port', 'Desconocido')}```", 
            inline=False)
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
    global status_message_id

    channel = bot.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        return

    data  = await query_server()
    embed = build_embed(data)

    try:
        if status_message_id:
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            status_message_id = msg.id
    except discord.NotFound:
        msg = await channel.send(embed=embed)
        status_message_id = msg.id
    except Exception as e:
        print(f"[ERROR] Discord no dejó actualizar el mensaje: {e}")

    estado = "🟢 ONLINE" if data["online"] else "🔴 OFFLINE"
    print(f"[{datetime.now(ZoneInfo('America/Santiago')).strftime('%H:%M:%S')}] {estado} | Jugadores: {data.get('players', '—')}")


@bot.event
async def on_ready():
        print(f"✅  Bot conectado como {bot.user}")
        update_status.start()


@bot.command(name="status")
async def cmd_status(ctx):
    data  = await query_server()
    embed = build_embed(data)
    await ctx.send(embed=embed)


@bot.command(name="setstatus")
@commands.has_permissions(administrator=True)
async def cmd_setstatus(ctx):
    global status_message_id, STATUS_CHANNEL_ID
    STATUS_CHANNEL_ID = ctx.channel.id
    status_message_id = None
    await ctx.message.delete()
    await update_status()

bot.run(os.getenv("DISCORD_TOKEN"))