"""
TallyInsights Desktop Backend Entry Point
==========================================
This is the PyInstaller entry point for the bundled backend.
It configures paths so SQLite and uploads go to the user's AppData folder,
then starts uvicorn serving the FastAPI app.
"""

import os
import sys

# ── PyInstaller bundle path setup ─────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller .exe — sys._MEIPASS is the bundle dir
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
    os.chdir(bundle_dir)

# ── User data directory (AppData\Roaming\TallyInsights) ──────────────────
appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
data_dir = os.path.join(appdata, 'TallyInsights')
uploads_dir = os.path.join(data_dir, 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

# Override config via environment so app/config.py picks them up
os.environ.setdefault('DATABASE_URL', f'sqlite:///{os.path.join(data_dir, "tallyinsights.db")}')
os.environ.setdefault('UPLOAD_DIR', uploads_dir)

# ── Start uvicorn ─────────────────────────────────────────────────────────
import uvicorn  # noqa: E402

if __name__ == '__main__':
    port = int(os.environ.get('TALLY_PORT', '8000'))
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=port,
        log_level='error',
        access_log=False,
    )
