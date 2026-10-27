# ============================================
# ShieldCV — Server Entry Point
# ============================================

import os
import sys
import uvicorn

# Ensure the parent directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def start():
    """Starts the ShieldCV FastAPI backend server on port 8000."""
    print("=" * 60)
    print("🛡️  Starting ShieldCV Security Backend Server...")
    print("   API Docs: http://localhost:8000/docs")
    print("   Health:   http://localhost:8000/api/status")
    print("=" * 60)
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    start()
