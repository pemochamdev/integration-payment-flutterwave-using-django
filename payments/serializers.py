
from rest_framework import serializers
from .models import PaymentTransaction
from django.contrib.auth.models import User



class UserPaymentSerializer(serializers.ModelSerializer):
    """Serialiseur pour les informations utilisateur dans les transactions"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = fields



class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serialiseur principal pour les transactions de paiement"""
    user = UserPaymentSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        write_only=True, 
        required=False
    )
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 
            'user', 
            'user_id',
            'transaction_reference', 
            'flutterwave_transaction_id',
            'amount', 
            'currency', 
            'status', 
            'payment_method',
            'created_at', 
            'updated_at',
            'customer_email'
        ]
        read_only_fields = [
            'id', 
            'transaction_reference', 
            'flutterwave_transaction_id', 
            'status', 
            'created_at', 
            'updated_at'
        ]

class PaymentInitiationSerializer(serializers.Serializer):
    """Serialiseur spécifique pour l'initiation de paiement"""
    amount = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        min_value=0.01,
        required=True
    )
    currency = serializers.CharField(
        max_length=5, 
        default='USD'
    )
    customer_email = serializers.EmailField(required=False)
    
    def validate_amount(self, value):
        """
        Validation personnalisée du montant
        """
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à zéro.")
        return value



class RefundSerializer(serializers.Serializer):
    """Serialiseur pour les demandes de remboursement"""
    reason = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=255
    )
    
    def validate_reason(self, value):
        """
        Validation personnalisée de la raison de remboursement
        """
        if value and len(value) < 3:
            raise serializers.ValidationError(
                "La raison du remboursement doit contenir au moins 3 caractères."
            )
        return value