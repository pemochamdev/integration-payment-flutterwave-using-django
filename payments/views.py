
# payments/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import PaymentTransaction
from .serializers import (
    PaymentTransactionSerializer, 
    PaymentInitiationSerializer,
    RefundSerializer
)
from .services import FlutterwavePaymentService
from .exceptions import PaymentException

class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la gestion des transactions de paiement
    Permet la lecture des transactions de l'utilisateur connecté
    """
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'currency', 'created_at']
    
    def get_queryset(self):
        """
        Limite les résultats aux transactions de l'utilisateur connecté
        """
        return PaymentTransaction.objects.filter(user=self.request.user)
    
    @action(
        detail=False, 
        methods=['POST'], 
        serializer_class=PaymentInitiationSerializer
    )
    def initiate(self, request):
        """
        Action personnalisée pour initier un paiement
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment_service = FlutterwavePaymentService()
        
        try:
            payment_data = payment_service.initiate_payment(
                user=request.user,
                amount=serializer.validated_data['amount'],
                currency=serializer.validated_data.get('currency', 'USD'),
                customer_details={
                    'email': serializer.validated_data.get('customer_email')
                }
            )
            return Response(payment_data, status=status.HTTP_201_CREATED)
        
        except PaymentException as e:
            return Response(
                {
                    "error": e.message,
                    "error_code": e.error_code
                }, 
                status=e.status_code
            )
    
    @action(
        detail=False, 
        methods=['GET'], 
        url_path='verify/(?P<transaction_reference>[^/.]+)'
    )
    def verify_transaction(self, request, transaction_reference=None):
        """
        Action personnalisée pour vérifier une transaction
        """
        payment_service = FlutterwavePaymentService()
        
        try:
            verification_result = payment_service.verify_transaction(transaction_reference)
            return Response(verification_result, status=status.HTTP_200_OK)
        
        except PaymentException as e:
            return Response(
                {
                    "error": e.message,
                    "error_code": e.error_code
                }, 
                status=e.status_code
            )
    
    @action(
        detail=True, 
        methods=['POST'], 
        url_path='refund',
        serializer_class=RefundSerializer
    )
    def refund_transaction(self, request, pk=None):
        """
        Action de remboursement pour une transaction spécifique
        """
        # Récupération de la transaction
        transaction = self.get_object()
        
        # Validation des données de la requête
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Préparation du service de paiement
        payment_service = FlutterwavePaymentService()
        
        try:
            # Exécution du remboursement
            refund_result = payment_service.refund_transaction(
                transaction,
                reason=serializer.validated_data.get('reason')
            )
            
            return Response(refund_result, status=status.HTTP_200_OK)
        
        except RefundException as e:
            return Response(
                {
                    "error": e.message,
                    "error_code": e.error_code
                }, 
                status=e.status_code
            )
    
    def get_permissions(self):
        """
        Permissions personnalisées
        """
        if self.action == 'refund_transaction':
            # Seuls les administrateurs peuvent effectuer des remboursements
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
