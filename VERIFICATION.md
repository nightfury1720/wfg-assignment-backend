# Backend Requirements Verification

## Success Criteria Testing

This document describes how to verify all 4 success criteria for the backend assignment.

**Key Architecture Points:**
- ✅ Tasks are queued in **Redis/Upstash** (not server memory)
- ✅ 30-second delay happens in **Celery worker** (not webhook handler)
- ✅ Transactions stored in **database** immediately (not server memory)
- ✅ Webhook responds immediately (<500ms) regardless of processing time

### Prerequisites

1. **Start Django Server:**
   ```bash
   cd backend
   source venv/bin/activate
   python manage.py runserver
   ```

2. **Start Celery Worker:**
   ```bash
   # In a separate terminal
   cd backend
   source venv/bin/activate
   celery -A config worker --loglevel=info
   ```

3. **Verify Redis/Upstash is accessible** (should be configured in .env)

### Running Verification Script

```bash
cd backend
source venv/bin/activate
pip install requests  # If not already installed
python verify_requirements.py
```

## Success Criteria

### 1. Single Transaction ✅

**Requirement:** Send one webhook → verify it's processed after ~30 seconds

**What happens:**
- Webhook received → Returns 202 immediately (<500ms)
- Transaction stored in database with status `PROCESSING`
- Task queued in Celery/Redis (not in server memory)
- After ~30 seconds, Celery worker processes the task
- Transaction status updated to `PROCESSED`

**Key Points:**
- ✅ Task is in Redis queue, not server memory
- ✅ 30-second delay happens in Celery worker, not webhook handler
- ✅ Webhook responds immediately regardless of processing time

### 2. Duplicate Prevention ✅

**Requirement:** Send the same webhook multiple times → verify only one transaction is processed

**What happens:**
- First webhook: Creates transaction, queues task, returns 202
- Duplicate webhooks: Detects existing transaction, returns 202 (no new task queued)
- Only one transaction exists in database
- Only one task is processed

**Key Points:**
- ✅ Idempotency check before creating transaction
- ✅ Graceful handling without errors
- ✅ No duplicate processing

### 3. Performance ✅

**Requirement:** Webhook endpoint responds quickly even under processing load

**What happens:**
- Multiple webhooks sent rapidly
- Each responds with 202 in <500ms
- Tasks queued in Redis (not blocking webhook handler)
- Processing happens asynchronously

**Key Points:**
- ✅ Response time <500ms regardless of processing complexity
- ✅ Tasks queued, not processed synchronously
- ✅ Server can handle multiple requests concurrently

### 4. Reliability ✅

**Requirement:** Service handles errors gracefully and doesn't lose transactions

**What happens:**
- Malformed JSON → Returns 400, no transaction created
- Missing fields → Returns 400, no transaction created
- Valid transactions still work after errors
- Transactions are persisted in database (not lost)

**Key Points:**
- ✅ Error handling for invalid requests
- ✅ Valid transactions are never lost
- ✅ Database persistence ensures reliability

## Architecture Flow

```
Webhook Request
    ↓
[Webhook Handler] ← Returns 202 immediately
    ↓
[Store in Database] ← Transaction with PROCESSING status
    ↓
[Queue Task in Celery/Redis] ← Task stored in Redis queue
    ↓
[Return 202] ← Response sent (<500ms)
    ↓
[30 seconds later...]
    ↓
[Celery Worker] ← Picks up task from Redis
    ↓
[Process Transaction] ← Updates status to PROCESSED
    ↓
[Update Database] ← Transaction marked as PROCESSED
```

## Important Notes

1. **Task Queue (Not Server Memory):**
   - Tasks are stored in Redis/Upstash queue
   - Not held in Django server memory
   - Survives server restarts (if Redis persists)

2. **30-Second Delay:**
   - Happens in Celery worker, not webhook handler
   - Webhook responds immediately
   - Processing is asynchronous

3. **Database Storage:**
   - Transaction stored immediately when webhook received
   - Status starts as `PROCESSING`
   - Updated to `PROCESSED` after 30 seconds

4. **Idempotency:**
   - Checked before creating transaction
   - Duplicate webhooks return 202 but don't create new transactions
   - No duplicate tasks queued

