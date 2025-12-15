# Transaction Webhook Service - Backend

A Django-based service that receives transaction webhooks from external payment processors and processes them reliably in the background using Celery.

## Features

- ✅ Webhook endpoint that accepts transaction data
- ✅ Health check endpoint
- ✅ Transaction query endpoint
- ✅ Background processing with 30-second delay
- ✅ Idempotency handling (duplicate webhook prevention)
- ✅ Fast response times (< 500ms)
- ✅ Persistent storage with PostgreSQL

## Tech Stack

- **Framework**: Django 4.2.7
- **API**: Django REST Framework
- **Database**: SQLAlchemy with PostgreSQL (Supabase)
- **Task Queue**: Celery with Redis (Upstash)
- **Python**: 3.9+

## Prerequisites

- Python 3.9 or higher
- Supabase PostgreSQL database (configured via .env)
- Upstash Redis (configured via .env)

## Setup Instructions

### 1. Clone and Navigate

```bash
cd backend
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Variables

You can either run the setup script or create a `.env` file manually:

**Option 1: Use setup script (recommended)**
```bash
./setup_env.sh
```

**Option 2: Create .env manually**

Create a `.env` file in the `backend` directory:

```env
# Supabase Database Connection
DATABASE_URL=postgresql://postgres:3h9He*qGc9cD5Qu@db.qiudtvmfrdwjnlneawfy.supabase.co:5432/postgres

# Celery Configuration (Upstash Redis)
CELERY_BROKER_URL=redis://default:AU2oAAIncDExYjU3ZjQ4NGY3ZGI0MTUzOTBiZGE5N2Q1Y2M3MTYzMHAxMTk4ODA@exotic-shepherd-19880.upstash.io:6379
CELERY_RESULT_BACKEND=redis://default:AU2oAAIncDExYjU3ZjQ4NGY3ZGI0MTUzOTBiZGE5N2Q1Y2M3MTYzMHAxMTk4ODA@exotic-shepherd-19880.upstash.io:6379

# Django Secret Key (change in production)
SECRET_KEY=your-secret-key-here
```

**Note**: The `DATABASE_URL` uses Supabase PostgreSQL. You can also use individual database settings if preferred.

### 5. Database Setup

The database is already set up on Supabase. Create the tables using SQLAlchemy:

```bash
source venv/bin/activate
python -m transactions.init_db
```

This will test the connection and create the necessary tables.

### 6. Start Celery Worker

**Note**: Redis is hosted on Upstash, so no local Redis server is needed.

In a separate terminal:

```bash
source venv/bin/activate
celery -A config worker --loglevel=info
```

### 8. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Health Check
- **Endpoint**: `GET /`
- **Response**:
```json
{
  "status": "HEALTHY",
  "current_time": "2024-01-15T10:30:00Z"
}
```

### 2. Webhook Transaction
- **Endpoint**: `POST /v1/webhooks/transactions`
- **Status Code**: `202 Accepted`
- **Request Body**:
```json
{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": 1500,
  "currency": "INR"
}
```

### 3. Get Transaction
- **Endpoint**: `GET /v1/transactions/{transaction_id}`
- **Response**:
```json
[{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": "150.50",
  "currency": "USD",
  "status": "PROCESSED",
  "created_at": "2024-01-15T10:30:00Z",
  "processed_at": "2024-01-15T10:30:30Z"
}]
```

## Testing

### Test Single Transaction

```bash
curl -X POST http://localhost:8000/v1/webhooks/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_test_001",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500,
    "currency": "INR"
  }'
```

### Test Duplicate Prevention

Send the same webhook multiple times - only one transaction should be processed.

### Check Transaction Status

```bash
curl http://localhost:8000/v1/transactions/txn_test_001
```

### Health Check

```bash
curl http://localhost:8000/
```

## Technical Choices

1. **Django + DRF**: Chosen for rapid development and REST API framework
2. **SQLAlchemy**: Used for database operations with Supabase PostgreSQL for reliable transaction storage
3. **Celery + Upstash Redis**: Industry-standard task queue for background processing with cloud-hosted Redis
4. **30-Second Delay**: Implemented using `time.sleep(30)` in Celery task to simulate external API calls
5. **Idempotency**: Implemented by checking for existing transactions before creating new ones
6. **Fast Response**: Webhook endpoint immediately returns 202 and queues task, ensuring < 500ms response time

## Project Structure

```
backend/
├── config/              # Django project settings
├── transactions/        # Main app
│   ├── database.py      # SQLAlchemy database connection
│   ├── sqlalchemy_models.py # SQLAlchemy models
│   ├── views.py         # API endpoints
│   ├── serializers.py   # Request/response serializers
│   ├── tasks.py         # Celery background tasks
│   └── init_db.py       # Database initialization script
├── manage.py
├── requirements.txt
└── README.md
```

## Deployment

For production deployment:

1. Set `DEBUG = False` in settings
2. Configure proper `ALLOWED_HOSTS`
3. Use environment variables for sensitive data
4. Set up proper database backups
5. Configure Redis persistence
6. Use a process manager (supervisor/systemd) for Celery workers
7. Set up monitoring and logging

## License

MIT

