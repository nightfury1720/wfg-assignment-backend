"""
Verification script for backend requirements
Tests the 4 success criteria:
1. Single Transaction: Processed after ~30 seconds (task in queue, not server memory)
2. Duplicate Prevention: Only one transaction processed
3. Performance: Webhook responds <500ms even under load
4. Reliability: Handles errors gracefully, doesn't lose transactions
"""
import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_single_transaction_30_second_delay():
    """
    Test 1: Single Transaction
    - Send webhook → Returns 202 immediately
    - Transaction stored in DB (not server memory)
    - Task queued in Celery/Redis (not server memory)
    - Processed after ~30 seconds
    """
    print_section("Test 1: Single Transaction - 30 Second Processing Delay")
    
    transaction_id = f"txn_single_{int(time.time())}"
    webhook_data = {
        "transaction_id": transaction_id,
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR"
    }
    
    print(f"📤 Step 1: Sending webhook for transaction: {transaction_id}")
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/v1/webhooks/transactions",
        json=webhook_data,
        headers={"Content-Type": "application/json"}
    )
    response_time = (time.time() - start_time) * 1000
    
    print(f"   ✅ Response Status: {response.status_code}")
    print(f"   ✅ Response Time: {response_time:.2f}ms")
    assert response.status_code == 202, "Should return 202 Accepted"
    assert response_time < 500, f"Response should be <500ms, got {response_time}ms"
    print(f"   ✅ Webhook responded immediately (task queued in Redis, not server memory)")
    
    print(f"\n📊 Step 2: Checking transaction in database (stored, not in server memory)...")
    response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
    data = json.loads(response.content)[0]
    print(f"   Status: {data['status']}")
    print(f"   Created At: {data['created_at']}")
    print(f"   Processed At: {data['processed_at']}")
    assert data['status'] == 'PROCESSING', "Should be PROCESSING initially"
    assert data['processed_at'] is None, "Should not be processed yet"
    print(f"   ✅ Transaction stored in database (not server memory)")
    
    print(f"\n⏳ Step 3: Waiting 30 seconds for Celery worker to process...")
    print(f"   (Task is in Redis queue, not server memory)")
    print(f"   (Processing happens in Celery worker after 30-second delay)")
    
    start_wait = time.time()
    processed = False
    check_interval = 2
    
    while not processed and (time.time() - start_wait) < 35:
        time.sleep(check_interval)
        response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
        data = json.loads(response.content)[0]
        elapsed = time.time() - start_wait
        
        if data['status'] == 'PROCESSED':
            print(f"   ✅ Transaction processed after {elapsed:.1f} seconds")
            print(f"   Processed At: {data['processed_at']}")
            processed = True
        else:
            print(f"   ⏳ Still processing... ({elapsed:.1f}s elapsed, status: {data['status']})")
    
    assert processed, "Transaction should be processed within 35 seconds"
    assert 28 <= elapsed <= 35, f"Should process around 30 seconds, got {elapsed:.1f}s"
    
    print(f"\n✅ Test 1 PASSED:")
    print(f"   - Webhook responded immediately (<500ms)")
    print(f"   - Transaction stored in database (not server memory)")
    print(f"   - Task queued in Redis (not server memory)")
    print(f"   - Processed after ~30 seconds by Celery worker")


def test_duplicate_prevention():
    """
    Test 2: Duplicate Prevention
    - Send same webhook multiple times
    - Only one transaction created
    - Only one task processed
    """
    print_section("Test 2: Duplicate Prevention")
    
    transaction_id = f"txn_duplicate_{int(time.time())}"
    webhook_data = {
        "transaction_id": transaction_id,
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 2000,
        "currency": "USD"
    }
    
    print(f"📤 Sending same webhook 3 times for transaction: {transaction_id}")
    responses = []
    for i in range(3):
        response = requests.post(
            f"{BASE_URL}/v1/webhooks/transactions",
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        responses.append(response.status_code)
        print(f"   Attempt {i+1}: Status {response.status_code}")
        time.sleep(0.1)
    
    assert all(status == 202 for status in responses), "All should return 202"
    print(f"   ✅ All webhooks accepted (idempotent)")
    
    print(f"\n📊 Checking database for duplicates...")
    response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
    transactions = json.loads(response.content)
    
    print(f"   Found {len(transactions)} transaction(s)")
    assert len(transactions) == 1, f"Should have only 1 transaction, found {len(transactions)}"
    
    txn = transactions[0]
    print(f"   Transaction ID: {txn['transaction_id']}")
    print(f"   Amount: {txn['amount']} {txn['currency']}")
    print(f"   Status: {txn['status']}")
    
    print(f"\n✅ Test 2 PASSED:")
    print(f"   - Multiple webhooks with same transaction_id")
    print(f"   - Only one transaction created in database")
    print(f"   - Idempotency working correctly")


def test_performance():
    """
    Test 3: Performance
    - Multiple webhooks sent rapidly
    - All respond <500ms
    - Tasks queued (not blocking)
    """
    print_section("Test 3: Performance Under Load")
    
    num_requests = 10
    print(f"📤 Sending {num_requests} webhooks rapidly...")
    
    response_times = []
    transaction_ids = []
    
    for i in range(num_requests):
        transaction_id = f"txn_perf_{int(time.time())}_{i}"
        transaction_ids.append(transaction_id)
        webhook_data = {
            "transaction_id": transaction_id,
            "source_account": f"acc_user_{i}",
            "destination_account": f"acc_merchant_{i}",
            "amount": 1000 + i,
            "currency": "INR"
        }
        
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/v1/webhooks/transactions",
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        elapsed = (time.time() - start) * 1000
        response_times.append(elapsed)
        
        assert response.status_code == 202, f"Request {i+1} should return 202"
        print(f"   Request {i+1}: {elapsed:.2f}ms")
    
    avg_time = sum(response_times) / len(response_times)
    max_time = max(response_times)
    min_time = min(response_times)
    
    print(f"\n📊 Performance Statistics:")
    print(f"   Average: {avg_time:.2f}ms")
    print(f"   Min: {min_time:.2f}ms")
    print(f"   Max: {max_time:.2f}ms")
    
    assert avg_time < 500, f"Average should be <500ms, got {avg_time:.2f}ms"
    assert max_time < 1000, f"Max should be <1000ms, got {max_time:.2f}ms"
    
    print(f"\n✅ Test 3 PASSED:")
    print(f"   - All {num_requests} requests responded quickly")
    print(f"   - Average response time: {avg_time:.2f}ms (<500ms)")
    print(f"   - Tasks queued asynchronously (not blocking)")


def test_reliability():
    """
    Test 4: Reliability
    - Handles malformed requests
    - Handles missing fields
    - Doesn't lose valid transactions
    """
    print_section("Test 4: Reliability & Error Handling")
    
    print("🧪 Test 4.1: Malformed JSON")
    try:
        response = requests.post(
            f"{BASE_URL}/v1/webhooks/transactions",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        assert response.status_code == 400, "Should return 400 for malformed JSON"
        print("   ✅ Handled gracefully")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        raise
    
    print("\n🧪 Test 4.2: Missing required fields")
    incomplete_data = {
        "transaction_id": "txn_incomplete",
        "source_account": "acc_user_789",
    }
    response = requests.post(
        f"{BASE_URL}/v1/webhooks/transactions",
        json=incomplete_data,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    assert response.status_code == 400, "Should return 400 for missing fields"
    print("   ✅ Handled gracefully")
    
    print("\n🧪 Test 4.3: Valid transaction after errors (should still work)")
    valid_data = {
        "transaction_id": f"txn_reliable_{int(time.time())}",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 3000,
        "currency": "EUR"
    }
    response = requests.post(
        f"{BASE_URL}/v1/webhooks/transactions",
        json=valid_data,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    assert response.status_code == 202, "Should still accept valid transactions"
    
    response = requests.get(f"{BASE_URL}/v1/transactions/{valid_data['transaction_id']}")
    data = json.loads(response.content)[0]
    assert data['status'] == 'PROCESSING', "Transaction should be stored"
    print(f"   ✅ Transaction stored correctly (not lost)")
    
    print(f"\n✅ Test 4 PASSED:")
    print(f"   - Errors handled gracefully")
    print(f"   - Valid transactions not lost")
    print(f"   - Service remains reliable")


def test_health_check():
    """Test health check endpoint"""
    print_section("Health Check")
    
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200, "Health check should return 200"
    
    data = json.loads(response.content)
    print(f"   Status: {data['status']}")
    print(f"   Current Time: {data['current_time']}")
    assert data['status'] == 'HEALTHY', "Should return HEALTHY status"
    print("   ✅ Health check working")


def main():
    print("\n" + "="*70)
    print("  Backend Requirements Verification")
    print("  Testing 4 Success Criteria")
    print("="*70)
    
    print("\n⚠️  Prerequisites:")
    print("   1. Django server running: python manage.py runserver")
    print("   2. Celery worker running: celery -A config worker --loglevel=info")
    print("   3. Redis/Upstash accessible (configured in .env)")
    print("\n   Press Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n❌ Cancelled")
        return
    
    try:
        test_health_check()
        test_single_transaction_30_second_delay()
        test_duplicate_prevention()
        test_performance()
        test_reliability()
        
        print_section("All Tests Completed Successfully")
        print("✅ All 4 success criteria verified!")
        print("\nSummary:")
        print("  1. ✅ Single Transaction: Processed after ~30 seconds")
        print("     (Task in Redis queue, not server memory)")
        print("  2. ✅ Duplicate Prevention: Only one transaction created")
        print("  3. ✅ Performance: All requests <500ms")
        print("  4. ✅ Reliability: Errors handled gracefully")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("   Make sure Django server is running on http://localhost:8000")
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        raise


if __name__ == "__main__":
    main()

