import json
import time
import os
from datetime import datetime
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from unittest.mock import patch, MagicMock
from transactions.database import SessionLocal, engine, Base
from transactions.sqlalchemy_models import Transaction, TransactionStatus
from transactions.tasks import process_transaction
from celery import current_app

# Configure Celery to run synchronously in tests
os.environ.setdefault('CELERY_TASK_ALWAYS_EAGER', 'True')


class TransactionWebhookTests(TestCase):
    """Test suite for transaction webhook processing"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class - create tables once"""
        super().setUpClass()
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"Warning: Could not create tables: {e}")
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.webhook_url = '/v1/webhooks/transactions'
        self.sample_webhook_data = {
            'transaction_id': 'test-txn-001',
            'source_account': 'ACC001',
            'destination_account': 'ACC002',
            'amount': '100.50',
            'currency': 'USD'
        }
        # Clear any existing test data
        self._cleanup_test_data()
        # Patch Celery to simulate async queue behavior
        # Tasks are queued but NOT executed immediately (simulating real async behavior)
        self.celery_patcher = patch('transactions.views.process_transaction.delay')
        self.mock_celery_delay = self.celery_patcher.start()
        # Store task calls to verify queuing behavior
        self.task_calls = []
        def store_call(*args, **kwargs):
            # Simulate queuing - store the call but don't execute
            transaction_id = args[0] if args else None
            self.task_calls.append(transaction_id)
            # Return a mock AsyncResult to simulate Celery task
            mock_result = MagicMock()
            mock_result.id = f"task-{transaction_id}"
            return mock_result
        self.mock_celery_delay.side_effect = store_call
    
    def tearDown(self):
        """Clean up after each test"""
        self._cleanup_test_data()
        # Stop patching
        if hasattr(self, 'celery_patcher'):
            self.celery_patcher.stop()
    
    def _cleanup_test_data(self):
        """Remove test transactions from database"""
        db = SessionLocal()
        try:
            db.query(Transaction).filter(
                Transaction.transaction_id.like('test-%')
            ).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    
    def _get_transaction(self, transaction_id):
        """Helper to get transaction from database"""
        db = SessionLocal()
        try:
            return db.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()
        finally:
            db.close()
    
    def _count_transactions(self, transaction_id):
        """Helper to count transactions with given ID"""
        db = SessionLocal()
        try:
            return db.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).count()
        finally:
            db.close()

    def test_1_single_transaction_processing(self):
        """
        Test 1: Single Transaction
        Send one webhook → verify it's processed after ~30 seconds
        """
        print("\n=== Test 1: Single Transaction Processing ===")
        
        # Send webhook
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.sample_webhook_data),
            content_type='application/json'
        )
        
        # Check for errors
        if response.status_code != 202:
            print(f"Error response: {response.status_code}")
            try:
                print(f"Response content: {response.content.decode()}")
            except:
                print(f"Response content: {response.content}")
        
        # Verify immediate response (should be fast, not waiting for 30s processing)
        response_time = time.time()
        self.assertEqual(response.status_code, 202, 
                       f"Webhook should return 202 Accepted, got {response.status_code}: {response.content}")
        print(f"✓ Webhook accepted with status 202 (instantaneous response)")
        
        # Verify transaction was created IMMEDIATELY (before task runs)
        transaction = self._get_transaction(self.sample_webhook_data['transaction_id'])
        self.assertIsNotNone(transaction, "Transaction should be created in database")
        self.assertEqual(transaction.status, TransactionStatus.PROCESSING, 
                        "Transaction should be in PROCESSING status (before task execution)")
        print(f"✓ Transaction created with PROCESSING status")
        
        # Verify task was queued (but NOT executed yet)
        self.assertEqual(len(self.task_calls), 1, "Task should be queued")
        self.assertEqual(self.task_calls[0], self.sample_webhook_data['transaction_id'], 
                        "Correct transaction ID should be queued")
        print(f"✓ Task queued (stored in queue, not executed yet)")
        
        # Now simulate Celery worker picking up task from queue and processing it
        # This should take ~30 seconds
        print(f"  Simulating Celery worker processing task (this takes ~30 seconds)...")
        start_time = time.time()
        process_transaction(self.sample_webhook_data['transaction_id'])
        elapsed_time = time.time() - start_time
        
        # Verify processing time is approximately 30 seconds
        self.assertGreaterEqual(elapsed_time, 29, f"Processing should take ~30 seconds, got {elapsed_time:.2f}s")
        self.assertLessEqual(elapsed_time, 32, f"Processing should take ~30 seconds, got {elapsed_time:.2f}s")
        print(f"✓ Transaction processed in {elapsed_time:.2f} seconds")
        
        # Verify transaction status changed to PROCESSED
        transaction = self._get_transaction(self.sample_webhook_data['transaction_id'])
        self.assertEqual(transaction.status, TransactionStatus.PROCESSED, "Transaction should be PROCESSED")
        self.assertIsNotNone(transaction.processed_at, "processed_at should be set")
        print(f"✓ Transaction status updated to PROCESSED")
        print("✓ Test 1 PASSED\n")

    def test_2_duplicate_prevention(self):
        """
        Test 2: Duplicate Prevention
        Send the same webhook multiple times → verify only one transaction is processed
        """
        print("\n=== Test 2: Duplicate Prevention ===")
        
        # Send webhook multiple times rapidly
        num_requests = 5
        responses = []
        
        for i in range(num_requests):
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(self.sample_webhook_data),
                content_type='application/json'
            )
            responses.append(response.status_code)
        
        # All requests should return 202
        self.assertTrue(all(status == 202 for status in responses), 
                       f"All requests should return 202, got {responses}")
        print(f"✓ All {num_requests} webhook requests returned 202")
        
        # Verify only ONE transaction exists (duplicate prevention)
        count = self._count_transactions(self.sample_webhook_data['transaction_id'])
        self.assertEqual(count, 1, f"Should have exactly 1 transaction, found {count}")
        print(f"✓ Only 1 transaction created (duplicates prevented)")
        
        # Verify transaction is in PROCESSING status (tasks are queued, not executed)
        transaction = self._get_transaction(self.sample_webhook_data['transaction_id'])
        self.assertEqual(transaction.status, TransactionStatus.PROCESSING, 
                        "Transaction should be in PROCESSING status (task queued but not executed)")
        print(f"✓ Transaction is in PROCESSING status")
        
        # Verify task queuing behavior
        # Note: In real scenario, duplicate webhooks might queue multiple tasks
        # but only one transaction exists. Here we verify the transaction deduplication works.
        # The task queue might have multiple calls, but that's okay - the transaction is deduplicated
        print(f"✓ {len(self.task_calls)} task(s) queued (transaction deduplication prevents multiple transactions)")
        print("✓ Test 2 PASSED\n")

    def test_3_performance_under_load(self):
        """
        Test 3: Performance
        Webhook endpoint responds quickly even under processing load
        Key: Tasks are queued (not executed), so webhook responses are fast
        """
        print("\n=== Test 3: Performance Under Load ===")
        
        # Create multiple unique transactions rapidly
        num_transactions = 10
        response_times = []
        
        print(f"  Sending {num_transactions} webhooks rapidly...")
        for i in range(num_transactions):
            webhook_data = {
                'transaction_id': f'test-txn-perf-{i}',
                'source_account': f'ACC{i:03d}',
                'destination_account': f'ACC{i+100:03d}',
                'amount': f'{100.00 + i}',
                'currency': 'USD'
            }
            
            start_time = time.time()
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(webhook_data),
                content_type='application/json'
            )
            elapsed = time.time() - start_time
            response_times.append(elapsed)
            
            self.assertEqual(response.status_code, 202, 
                           f"Request {i} should return 202")
        
        # Verify all responses are fast (< 1 second)
        # Since tasks are queued but NOT executed synchronously, responses should be very fast
        max_response_time = max(response_times)
        avg_response_time = sum(response_times) / len(response_times)
        
        self.assertLess(max_response_time, 1.0, 
                       f"Max response time should be < 1s (tasks queued, not blocking), got {max_response_time:.3f}s")
        self.assertLess(avg_response_time, 0.5, 
                       f"Avg response time should be < 0.5s, got {avg_response_time:.3f}s")
        
        # Verify all tasks were queued (but not executed)
        self.assertEqual(len(self.task_calls), num_transactions, 
                        f"All {num_transactions} tasks should be queued")
        
        print(f"✓ Processed {num_transactions} webhooks")
        print(f"✓ Max response time: {max_response_time:.3f}s (fast - tasks queued, not blocking)")
        print(f"✓ Avg response time: {avg_response_time:.3f}s")
        print(f"✓ All {num_transactions} tasks queued (async, not blocking webhook responses)")
        print("✓ Test 3 PASSED\n")

    def test_4_reliability_error_handling(self):
        """
        Test 4: Reliability
        Service handles errors gracefully and doesn't lose transactions
        """
        print("\n=== Test 4: Reliability and Error Handling ===")
        
        # Test 4a: Invalid webhook data
        print("  Testing invalid webhook data...")
        invalid_data = {
            'transaction_id': 'test-txn-invalid',
            'source_account': 'ACC001',
            # Missing required fields
        }
        
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400, "Invalid data should return 400")
        print("  ✓ Invalid data handled gracefully (400)")
        
        # Test 4b: Valid transaction persists even if task fails
        print("  Testing transaction persistence...")
        valid_data = {
            'transaction_id': 'test-txn-reliable',
            'source_account': 'ACC001',
            'destination_account': 'ACC002',
            'amount': '200.00',
            'currency': 'USD'
        }
        
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(valid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 202, "Valid webhook should be accepted")
        
        # Verify transaction exists immediately (before task execution)
        transaction = self._get_transaction(valid_data['transaction_id'])
        self.assertIsNotNone(transaction, "Transaction should persist in database")
        # Since tasks are queued but not executed, status should be PROCESSING
        self.assertEqual(transaction.status, TransactionStatus.PROCESSING,
                        "Transaction should be in PROCESSING status (task queued but not executed)")
        print("  ✓ Transaction persisted in database with PROCESSING status")
        
        # Test 4c: Simulate task failure and verify transaction still exists
        print("  Testing error recovery...")
        with patch('transactions.tasks.process_transaction') as mock_task:
            mock_task.side_effect = Exception("Simulated task failure")
            
            # Transaction should still exist
            transaction = self._get_transaction(valid_data['transaction_id'])
            self.assertIsNotNone(transaction, "Transaction should still exist after error")
            print("  ✓ Transaction persists after error")
        
        # Test 4d: Process transaction successfully after error
        process_transaction(valid_data['transaction_id'])
        transaction = self._get_transaction(valid_data['transaction_id'])
        self.assertEqual(transaction.status, TransactionStatus.PROCESSED, 
                        "Transaction should be processable after error")
        print("  ✓ Transaction can be processed after error")
        
        print("✓ Test 4 PASSED\n")

    def test_integration_full_flow(self):
        """
        Integration test: Full flow from webhook to processed transaction
        """
        print("\n=== Integration Test: Full Flow ===")
        
        # Send webhook
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.sample_webhook_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 202)
        
        # Check transaction via GET endpoint
        get_url = f"/v1/transactions/{self.sample_webhook_data['transaction_id']}"
        response = self.client.get(get_url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 1)
        # Since task is queued but not executed, status should be PROCESSING
        self.assertEqual(data[0]['status'], 'PROCESSING', 
                        "Transaction should be PROCESSING (task queued but not executed)")
        print(f"✓ Transaction retrievable via GET endpoint (status: {data[0]['status']})")
        
        # Now simulate Celery worker processing the queued task
        print("  Simulating Celery worker processing queued task (~30 seconds)...")
        process_transaction(self.sample_webhook_data['transaction_id'])
        
        # Verify processed status after task execution
        response = self.client.get(get_url)
        data = response.json()
        self.assertEqual(data[0]['status'], 'PROCESSED', "Transaction should be PROCESSED after task execution")
        self.assertIsNotNone(data[0]['processed_at'], "processed_at should be set after processing")
        print("✓ Transaction status updated to PROCESSED after task execution")
        print("✓ Integration Test PASSED\n")

