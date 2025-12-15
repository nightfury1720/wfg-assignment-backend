from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
from django.http import JsonResponse
from .serializers import TransactionWebhookSerializer
from .tasks import process_transaction
from .database import SessionLocal
from .sqlalchemy_models import Transaction, TransactionStatus
from sqlalchemy.exc import IntegrityError


@api_view(['GET'])
def health_check(request):
    return JsonResponse({
        'status': 'HEALTHY',
        'current_time': datetime.utcnow().isoformat() + 'Z',
    })


@api_view(['POST'])
def webhook_transaction(request):
    serializer = TransactionWebhookSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    transaction_id = data['transaction_id']
    
    db = SessionLocal()
    try:
        existing_transaction = db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
        
        if existing_transaction:
            return Response(status=status.HTTP_202_ACCEPTED)
        
        new_transaction = Transaction(
            transaction_id=transaction_id,
            source_account=data['source_account'],
            destination_account=data['destination_account'],
            amount=data['amount'],
            currency=data['currency'],
            status=TransactionStatus.PROCESSING,
        )
        
        db.add(new_transaction)
        db.commit()
        
        process_transaction.delay(transaction_id)
        
        return Response(status=status.HTTP_202_ACCEPTED)
    except IntegrityError:
        db.rollback()
        return Response(status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        db.rollback()
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        db.close()


@api_view(['GET'])
def get_transaction(request, transaction_id):
    db = SessionLocal()
    try:
        transaction = db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
        
        if not transaction:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        result = [{
            'transaction_id': transaction.transaction_id,
            'source_account': transaction.source_account,
            'destination_account': transaction.destination_account,
            'amount': float(transaction.amount),
            'currency': transaction.currency,
            'status': transaction.status.value,
            'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None,
        }]
        
        return Response(result)
    finally:
        db.close()
