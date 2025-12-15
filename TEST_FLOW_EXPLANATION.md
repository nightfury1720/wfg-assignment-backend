# Transaction Webhook Processing Flow

## What I Understood - Complete Flow

### Expected Behavior:

1. **Webhook Reception** (`POST /v1/webhooks/transactions`)
   - Receive webhook payload with transaction data
   - Validate data using serializer
   - **Return 202 Accepted IMMEDIATELY** (non-blocking)

2. **Duplicate Prevention**
   - Check if transaction_id already exists in database
   - If exists → Return 202 (already processed/processing)
   - If new → Continue to step 3

3. **Transaction Creation**
   - Create new Transaction record with:
     - transaction_id (primary key)
     - source_account, destination_account, amount, currency
     - status = PROCESSING
     - created_at = current timestamp
   - Save to database

4. **Task Queuing** (Async - Non-blocking)
   - Queue `process_transaction.delay(transaction_id)` to Celery
   - Task is stored in Redis queue
   - **DOES NOT wait for task execution**
   - Return 202 Accepted immediately

5. **Celery Worker Processing** (Async - Happens later)
   - Celery worker picks up task from queue
   - Task executes `process_transaction(transaction_id)`
   - Sleep for 30 seconds (simulating processing time)
   - Update transaction:
     - status = PROCESSED
     - processed_at = current timestamp
   - Commit to database

### Key Points:

✅ **Webhook responds instantly** - Does NOT wait for 30-second processing
✅ **Tasks are queued** - Stored in Redis queue, processed asynchronously
✅ **Duplicate prevention** - Database constraint prevents duplicate transactions
✅ **Fast responses under load** - Webhook endpoint doesn't block on task execution

### Test Verification:

1. **Test 1: Single Transaction**
   - Send webhook → Verify 202 response (fast)
   - Verify transaction created with PROCESSING status
   - Verify task queued
   - Manually execute task → Verify 30-second processing time
   - Verify status changes to PROCESSED

2. **Test 2: Duplicate Prevention**
   - Send same webhook 5 times rapidly
   - Verify all return 202
   - Verify only 1 transaction exists
   - Verify transaction in PROCESSING status

3. **Test 3: Performance**
   - Send 10 webhooks rapidly
   - Verify all respond in < 1 second
   - Verify tasks are queued (not blocking responses)

4. **Test 4: Reliability**
   - Test invalid data handling
   - Test transaction persistence
   - Test error recovery

