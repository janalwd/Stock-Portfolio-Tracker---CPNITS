import os
import secrets

from app import app

# Use Render's SECRET_KEY when configured; otherwise create a secure key
# for the current running instance instead of using the placeholder in app.py.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
