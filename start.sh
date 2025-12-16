#!/bin/bash
set -e

PORT=${PORT:-10000}

# Start uvicorn with ASGI application
exec uvicorn config.asgi:application \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 2 \
    --log-level info \
    --access-log

