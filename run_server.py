#!/usr/bin/env python3
"""
Apple Music Downloader Backend Server
Run this script to start the FastAPI backend server.
"""

import sys
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    from app.setting.setting import HOST, PORT, RELOAD
    
    # Configuration from settings
    host = HOST
    port = PORT
    reload = RELOAD
    
    print(f"🚀 Starting Apple Music Downloader Backend...")
    print(f"📍 Server: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"❤️  Health: http://{host}:{port}/health")
    print(f"🔄 Auto-reload: {'ON' if reload else 'OFF'}")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)