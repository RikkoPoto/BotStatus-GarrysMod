import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

class MainBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="$", intents=intents)

    async def setup_hook(self):
        # Lista de cogs a cargar (Aquí agregamos el nuevo de moderación)
        modulos = [
            "cogs.status_cog",
            "cogs.rangos_cog"
        ]
        
        for modulo in modulos:
            try:
                await self.load_extension(modulo)
                print(f"✅ Módulo {modulo} cargado exitosamente.")
            except Exception as e:
                print(f"❌ Error al cargar el módulo {modulo}: {e}")
                
        print("🔧 Proceso de carga de módulos finalizado.")

    async def on_ready(self):
        print(f"🚀 Bot iniciado y conectado como {self.user}")

if __name__ == "__main__":
    bot = MainBot()
    bot.run(os.getenv("DISCORD_TOKEN"))