#!/usr/bin/env python3
"""
Redis Connection Test Script

This script tests the Redis connection and cache setup for the qblog application.
Run this script to verify your Redis configuration before starting the main application.
"""

import os

import redis
from dotenv import load_dotenv


def test_redis_connection():
    load_dotenv()
    redis_url = os.getenv('REDIS_URL')
    
    if not redis_url:
        print("❌ No REDIS_URL found in environment variables")
        print("ℹ️  Application will use SimpleCache as fallback")
        return False
    
    print(f"🔍 Testing Redis connection to: {redis_url}")
    
    try:
        # Test Redis connection
        redis_client = redis.from_url(redis_url)
        redis_client.ping()
        print("✅ Redis connection successful!")
        
        # Test basic operations
        redis_client.set('test_key', 'test_value', ex=60)
        value = redis_client.get('test_key')
        if value and value.decode() == 'test_value':
            print("✅ Redis read/write operations working")
        else:
            print("❌ Redis read/write test failed")
            return False
        
        # Cleanup
        redis_client.delete('test_key')
        print("✅ Redis cleanup successful")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("ℹ️  Application will use SimpleCache as fallback")
        return False
    except redis.TimeoutError as e:
        print(f"❌ Redis timeout: {e}")
        print("ℹ️  Application will use SimpleCache as fallback")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("ℹ️  Application will use SimpleCache as fallback")
        return False

if __name__ == "__main__":
    print("🚀 Redis Connection Test for qblog")
    print("=" * 40)
    
    success = test_redis_connection()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Redis is ready! Your application will use Redis caching.")
    else:
        print("⚠️  Redis not available. Application will use in-memory caching.")
        print("   This is fine for development but not recommended for production.")
    
    print("\nTo fix Redis issues:")
    print("1. Make sure Redis server is running")
    print("2. Check your REDIS_URL in .env file")
    print("3. Verify network connectivity to Redis server")
