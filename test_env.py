#!/usr/bin/env python3
"""Test script to check if .env file is loaded correctly"""

from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

print("=== Environment Variables Test ===")
print(f"REDIS_CLOUD_PASSWORD: {os.getenv('REDIS_CLOUD_PASSWORD')}")
print(f"WRAPPER_USERNAME: {os.getenv('WRAPPER_USERNAME')}")
print(f"WRAPPER_PASSWORD: {os.getenv('WRAPPER_PASSWORD')}")
print(f"SPOTIFY_CLIENT_ID: {os.getenv('SPOTIFY_CLIENT_ID')}")

# Test Redis Cloud password specifically
redis_password = os.getenv('REDIS_CLOUD_PASSWORD')
if redis_password:
    print(f"✅ REDIS_CLOUD_PASSWORD loaded successfully: {redis_password[:10]}...")
else:
    print("❌ REDIS_CLOUD_PASSWORD not found in environment")
