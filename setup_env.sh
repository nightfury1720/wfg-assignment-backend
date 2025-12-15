#!/bin/bash

# Setup script for backend environment

echo "Setting up backend environment..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Supabase Database Connection (for SQLAlchemy)
user=postgres
password=3h9He*qGc9cD5Qu
host=db.qiudtvmfrdwjnlneawfy.supabase.co
port=5432
dbname=postgres

# Celery Configuration (Upstash Redis)
CELERY_BROKER_URL=redis://default:AU2oAAIncDExYjU3ZjQ4NGY3ZGI0MTUzOTBiZGE5N2Q1Y2M3MTYzMHAxMTk4ODA@exotic-shepherd-19880.upstash.io:6379
CELERY_RESULT_BACKEND=redis://default:AU2oAAIncDExYjU3ZjQ4NGY3ZGI0MTUzOTBiZGE5N2Q1Y2M3MTYzMHAxMTk4ODA@exotic-shepherd-19880.upstash.io:6379

# Django Secret Key (change in production)
SECRET_KEY=django-insecure-change-this-in-production
EOF
    echo ".env file created successfully!"
else
    echo ".env file already exists. Skipping creation."
fi

echo "Setup complete!"

