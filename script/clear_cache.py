#!/usr/bin/env python3
"""
Utility script to clear cache when moving download directories.
Use this script when you change the download paths in config.yaml.
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.redis import get_redis, is_redis_available


def clear_cache():
    """Clear all cache data from Redis."""
    if not is_redis_available():
        print("❌ Redis is not available. Cache system is disabled.")
        return False
    
    redis = get_redis()
    if not redis:
        print("❌ Failed to connect to Redis.")
        return False
    
    try:
        # Clear all cache-related keys
        patterns = ["dir:*", "cache:*", "lock:dir:*"]
        total_cleared = 0
        
        for pattern in patterns:
            keys = list(redis.scan_iter(match=pattern))
            if keys:
                redis.delete(*keys)
                total_cleared += len(keys)
                print(f"✅ Cleared {len(keys)} keys matching '{pattern}'")
        
        if total_cleared == 0:
            print("ℹ️  No cache data found to clear.")
        else:
            print(f"✅ Successfully cleared {total_cleared} cache entries.")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to clear cache: {e}")
        return False


def main():
    """Main function."""
    print("🧹 Apple Music Downloader - Cache Clear Utility")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("""
Usage: python clear_cache.py

This script clears all cache data from Redis.
Use this when you change download paths in config.yaml to avoid
cache inconsistencies.

The script will clear:
- Directory TTL tracking (dir:*)
- Cache metadata (cache:*)
- Directory locks (lock:dir:*)
""")
        return
    
    print("⚠️  This will clear ALL cache data from Redis.")
    print("   Use this when you change download paths in config.yaml.")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🚀 Force mode enabled, clearing cache...")
    else:
        response = input("\nDo you want to continue? (y/N): ").strip().lower()
        if response not in ["y", "yes"]:
            print("❌ Operation cancelled.")
            return
    
    success = clear_cache()
    
    if success:
        print("\n✅ Cache cleared successfully!")
        print("💡 You can now restart the backend server.")
    else:
        print("\n❌ Failed to clear cache.")
        sys.exit(1)


if __name__ == "__main__":
    main()
