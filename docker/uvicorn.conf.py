# Uvicorn configuration for Horilla-CRM
# This file provides advanced configuration options for the ASGI server

import multiprocessing
import os

# Bind settings
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
host = "0.0.0.0"
port = int(os.environ.get("PORT", "8000"))

# Worker settings
workers = int(os.environ.get("UVICORN_WORKERS", multiprocessing.cpu_count()))

# Application settings
app = "horilla.asgi:application"

# Logging
log_level = os.environ.get("UVICORN_LOG_LEVEL", "info")
access_log = True

# Development settings
reload = os.environ.get("UVICORN_RELOAD", "false").lower() == "true"

# WebSocket settings
ws_ping_interval = 20
ws_ping_timeout = 20

# SSL settings (if needed)
# ssl_keyfile = os.environ.get('SSL_KEYFILE')
# ssl_certfile = os.environ.get('SSL_CERTFILE')

# Additional ASGI settings
lifespan = "on"  # Enable ASGI lifespan protocol
