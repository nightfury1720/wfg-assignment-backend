from sqlalchemy import Column, String, Numeric, DateTime, Enum
from sqlalchemy.sql import func
from .database import Base
import enum


class TransactionStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"


class Transaction(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(String(255), primary_key=True, index=True)
    source_account = Column(String(255), nullable=False)
    destination_account = Column(String(255), nullable=False)
    amount = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PROCESSING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Transaction(transaction_id='{self.transaction_id}', status='{self.status}')>"

