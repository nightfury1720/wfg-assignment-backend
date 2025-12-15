from rest_framework import serializers


class TransactionWebhookSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=255)
    source_account = serializers.CharField(max_length=255)
    destination_account = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    currency = serializers.CharField(max_length=10)

