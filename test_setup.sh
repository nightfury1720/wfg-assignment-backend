#!/bin/bash

echo "=========================================="
echo "Backend Setup Test Script"
echo "=========================================="
echo ""

# Test 1: Environment Variables
echo "1. Testing environment variables..."
if [ -f .env ]; then
    echo "✅ .env file exists"
    source .env
    if [ -n "$user" ] && [ -n "$host" ] && [ -n "$dbname" ]; then
        echo "✅ Database environment variables are set"
    else
        echo "❌ Missing database environment variables"
        exit 1
    fi
    
    if [ -n "$CELERY_BROKER_URL" ] && [ -n "$CELERY_RESULT_BACKEND" ]; then
        echo "✅ Celery environment variables are set"
    else
        echo "❌ Missing Celery environment variables"
        exit 1
    fi
else
    echo "❌ .env file not found. Run ./setup_env.sh first"
    exit 1
fi

echo ""

# Test 2: Database Connection
echo "2. Testing database connection..."
source venv/bin/activate
python -c "from transactions.database import test_connection; exit(0 if test_connection() else 1)" 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database connection test passed"
else
    echo "❌ Database connection test failed"
    exit 1
fi

echo ""

# Test 3: Redis Connection
echo "3. Testing Redis connection..."
python -c "
import os
from dotenv import load_dotenv
import redis

load_dotenv()
redis_url = os.getenv('CELERY_BROKER_URL')

try:
    if redis_url.startswith('redis://'):
        redis_url_clean = redis_url.replace('redis://', '')
        if '@' in redis_url_clean:
            auth, host_port = redis_url_clean.split('@')
            password = auth.split(':')[1] if ':' in auth else None
            host, port = host_port.split(':')
            port = int(port)
        else:
            host, port = redis_url_clean.split(':')
            port = int(port)
            password = None
        
        r = redis.Redis(host=host, port=port, password=password, decode_responses=True, ssl=True)
        r.ping()
        print('✅ Redis connection successful')
    else:
        print('❌ Invalid Redis URL format')
        exit(1)
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Redis connection test passed"
else
    echo "❌ Redis connection test failed"
    exit 1
fi

echo ""

# Test 4: Celery Configuration
echo "4. Testing Celery configuration..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    from config.celery import app as celery_app
    print('✅ Celery app loaded successfully')
    print(f'✅ Broker: {celery_app.conf.broker_url.split(\"@\")[1] if \"@\" in celery_app.conf.broker_url else \"configured\"}')
    print(f'✅ Backend: {celery_app.conf.result_backend.split(\"@\")[1] if \"@\" in celery_app.conf.result_backend else \"configured\"}')
except Exception as e:
    print(f'❌ Celery configuration failed: {e}')
    exit(1)
" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Celery configuration test passed"
else
    echo "❌ Celery configuration test failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All tests passed! Setup is complete."
echo "=========================================="

