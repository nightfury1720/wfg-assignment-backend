# WFG Assignment - Backend Deployment Guide

## Deployment on Render

This backend is configured for deployment on Render using the `render.yaml` file.

### Prerequisites

1. A Render account
2. Supabase PostgreSQL database
3. Upstash Redis instance (or any Redis instance)

### Deployment Steps

1. **Push to Git Repository**
   - Push your code to GitHub, GitLab, or Bitbucket

2. **Create New Web Service on Render**
   - Go to Render Dashboard
   - Click "New +" → "Blueprint"
   - Connect your repository
   - Render will automatically detect `render.yaml` and create both web service and worker

3. **Configure Environment Variables**
   
   In the Render dashboard, add these environment variables:
   
   - `DATABASE_URL`: Your Supabase PostgreSQL connection string
   - `CELERY_BROKER_URL`: Your Redis connection URL (Upstash)
   - `CELERY_RESULT_BACKEND`: Your Redis connection URL (Upstash)
   - `SECRET_KEY`: Django secret key (generate a new one for production)
   - `DJANGO_SETTINGS_MODULE`: `config.settings`
   - `PYTHON_VERSION`: `3.9.18`

4. **Database Migration**
   
   After first deployment, run migrations:
   ```bash
   python manage.py migrate
   ```
   
   Or initialize database:
   ```bash
   python -m transactions.init_db
   ```

5. **Health Check**
   
   The service includes a health check endpoint at `/` that Render will use.

### Manual Deployment (Alternative)

If not using Blueprint:

1. **Create Web Service**
   - Type: Web Service
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn config.wsgi:application`
   - Environment: Python 3

2. **Create Worker Service**
   - Type: Background Worker
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `celery -A config worker --loglevel=info`
   - Environment: Python 3

### Production Settings

Before deploying, ensure:

- `DEBUG = False` in `config/settings.py`
- `ALLOWED_HOSTS` includes your Render domain
- All sensitive data is in environment variables
- `SECRET_KEY` is set via environment variable

### Health Check

The service exposes a health check endpoint:
- `GET /` - Returns service status

## License

MIT

