#!/bin/bash
export FLASK_APP=app.py
export FLASK_ENV=production
# Render fournit le port via $PORT
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 3