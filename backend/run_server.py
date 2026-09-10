import sys
import logging
from pathlib import Path

# Ensure backend directory is in path
sys.path.insert(0, str(Path(__file__).parent))

log_dir = Path(__file__).parent.parent / ".data"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "server_debug.log"

logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Starting Python server launcher...")

try:
    import uvicorn
    from app.main import app
    logging.info("Imported app successfully. Launching uvicorn on port 3001...")
    uvicorn.run(app, host="127.0.0.1", port=3001, log_level="info")
except Exception as e:
    logging.exception("Failed to start server")
