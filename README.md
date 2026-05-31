# 🤖 Bot de Estado — Garry's Mod + Discord

## Requisitos previos
- Python 3.10 o superior → https://python.org/downloads
- Una cuenta de Discord con acceso al servidor

---

## 1. Crear el Bot en Discord

1. Ve a https://discord.com/developers/applications
2. Clic en **New Application** → ponle un nombre (ej: "GMod Status")
3. Ve a la pestaña **Bot** → clic en **Add Bot**
4. En la sección **Token**, clic en **Reset Token** y copia el token
5. Activa el permiso **Send Messages** y **Read Message History** en Bot > Privileged Gateway Intents (no necesitas intents privilegiados para este bot)
6. Ve a **OAuth2 > URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Read Messages/View Channels`, `Embed Links`
7. Copia la URL generada, ábrela en el navegador e invita el bot a tu servidor

---

## 2. Configurar el proyecto

```bash
# Clonar / extraer los archivos en una carpeta, luego:
cd gmod_bot

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 3. Configurar las variables

### Token del bot
Crea un archivo llamado `.env` en la carpeta (copia `.env.example`):
```
DISCORD_TOKEN=pega_tu_token_aqui
```

### Variables en `bot.py`
Abre `bot.py` y edita la sección **CONFIGURACIÓN**:

```python
SERVER_IP   = "X"     # IP de tu servidor Gmod
SERVER_PORT = 27015                # Puerto (defecto Gmod: 27015)
QUERY_PORT  = 27015                # Puerto de query (normalmente igual)

STATUS_CHANNEL_ID = 123456789...   # ID del canal de Discord
UPDATE_INTERVAL   = 60             # Segundos entre actualizaciones
```

**¿Cómo obtener el ID del canal?**
En Discord: Ajustes → Avanzado → Activa "Modo desarrollador"
Luego clic derecho sobre el canal → "Copiar ID"

### Decorar el embed — sección `EMBED_CONFIG`
```python
EMBED_CONFIG = {
    "color_online":  0x57F287,   # Color hex cuando online (verde)
    "color_offline": 0xED4245,   # Color hex cuando offline (rojo)
    "thumbnail_url": "https://...",  # Logo del servidor (esquina superior derecha)
    "image_url":     "https://...",  # Banner grande en el embed
    "footer_text":   "🕹️ Mi Servidor GMod",
    "footer_icon":   "https://...",  # Ícono pequeño en el footer
}
```

---

## 4. Ejecutar el bot

```bash
python bot.py
```

Deberías ver:
```
✅  Bot conectado como GMod Status#1234
📡  Monitoreando 192.168.1.100:27015 cada 60s
[12:00:00] 🟢 ONLINE | Jugadores: 5
```

---

## Comandos disponibles

| Comando | Quién | Descripción |
|---------|-------|-------------|
| `!status` | Cualquiera | Muestra el estado en ese momento |
| `!setstatus` | Solo admins | Crea/mueve el mensaje de estado al canal actual |

---

## Notas importantes

- El bot **edita el mismo mensaje** cada vez que actualiza, para no llenar el canal
- Si el mensaje es borrado, el bot crea uno nuevo automáticamente
- El puerto de query de Gmod es generalmente el mismo que el de juego (27015)
- Asegúrate de que el **firewall** de tu servidor permita el puerto UDP de query
- Para correr el bot 24/7 puedes usar un VPS, Raspberry Pi, o servicios como Railway/Fly.io

---

## Estructura de archivos

```
gmod_bot/
├── bot.py            ← Bot principal
├── requirements.txt  ← Dependencias Python
├── .env              ← Token (NO subir a git)
└── .env.example      ← Plantilla del .env
```
