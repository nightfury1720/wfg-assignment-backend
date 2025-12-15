from celery import shared_task
from datetime import datetime
from .database import SessionLocal
from .sqlalchemy_models import Transaction, TransactionStatus
import time


@shared_task
def process_transaction(transaction_id):
    db = SessionLocal()
    try:
        transaction = db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
        
        if not transaction:
            return f"Transaction {transaction_id} not found"
        
        if transaction.status == TransactionStatus.PROCESSED:
            return f"Transaction {transaction_id} already processed"
        
        time.sleep(30)
        
        transaction.status = TransactionStatus.PROCESSED
        transaction.processed_at = datetime.utcnow()
        db.commit()
        
        return f"Transaction {transaction_id} processed successfully"
    except Exception as e:
        db.rollback()
        return f"Error processing transaction {transaction_id}: {str(e)}"
    finally:
        db.close()

