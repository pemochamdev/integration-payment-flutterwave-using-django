import logging
import requests
import uuid
from django.conf import settings
from django.db import transaction
from payments.models import PaymentTransaction
from payments.exceptions import PaymentInitiationError, PaymentVerificationError,RefundException

logger = logging.getLogger('payments')

class FlutterwavePaymentService:
    def __init__(self):
        self.base_url = settings.FLUTTERWAVE_BASE_URL
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        
    def generate_transaction_reference(self):
        """Génère une référence de transaction unique."""
        return f"FLW-{uuid.uuid4().hex[:12].upper()}"
    
    @transaction.atomic
    def initiate_payment(self, user, amount, currency='USD', customer_details=None):
        """
        Initie un paiement sécurisé avec enregistrement en base de données.
        
        Args:
            user (User): Utilisateur effectuant le paiement
            amount (float): Montant du paiement
            currency (str): Code devise
            customer_details (dict): Détails supplémentaires du client
        
        Returns:
            dict: Détails de la transaction
        """
        try:
            # Création de l'enregistrement de transaction
            transaction = PaymentTransaction.objects.create(
                user=user,
                amount=amount,
                currency=currency,
                transaction_reference=self.generate_transaction_reference(),
                customer_email=customer_details.get('email') if customer_details else None,
                status=PaymentTransaction.TransactionStatus.INITIATED
            )
            
            # Préparation payload pour Flutterwave
            payload = {
                "tx_ref": transaction.transaction_reference,
                "amount": str(amount),
                "currency": currency,
                "payment_options": "card,banktransfer,ussd",
                "redirect_url": settings.FLUTTERWAVE_REDIRECT_URL,
                "customer": {
                    "email": transaction.customer_email or user.email,
                    "name": f"{user.first_name} {user.last_name}",
                },
                "meta": {
                    "user_id": user.id,
                    "transaction_id": str(transaction.id)
                }
            }
            
            # Requête à l'API Flutterwave
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/payments", 
                json=payload, 
                headers=headers
            )
            
            # Gestion de la réponse
            response_data = response.json()
            
            if response.status_code != 200 or not response_data.get('status') == 'success':
                # Mise à jour du statut en cas d'échec
                transaction.status = PaymentTransaction.TransactionStatus.FAILED
                transaction.raw_response = response_data
                transaction.save()
                
                logger.error(f"Payment Initiation Failed: {response_data}")
                raise PaymentInitiationError(
                    message="Échec de l'initiation du paiement",
                    error_code=response_data.get('message', 'UNKNOWN_ERROR')
                )
            
            # Mise à jour de la transaction
            transaction.flutterwave_transaction_id = response_data.get('data', {}).get('id')
            transaction.raw_response = response_data
            transaction.status = PaymentTransaction.TransactionStatus.PENDING
            transaction.save()
            
            return {
                "transaction_reference": transaction.transaction_reference,
                "payment_link": response_data['data']['link']
            }
        
        except requests.exceptions.RequestException as e:
            logger.exception("Erreur réseau lors de l'initiation du paiement")
            raise PaymentInitiationError(str(e))
        except Exception as e:
            logger.exception("Erreur inattendue lors de l'initiation du paiement")
            raise PaymentInitiationError(str(e))
    
    @transaction.atomic
    def verify_transaction(self, transaction_reference):
        """
        Vérifie une transaction Flutterwave et met à jour son statut.
        
        Args:
            transaction_reference (str): Référence de transaction
        
        Returns:
            dict: Résultat de la vérification
        """
        try:
            # Récupération de la transaction
            transaction = PaymentTransaction.objects.get(
                transaction_reference=transaction_reference
            )
            
            # Requête de vérification
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/transactions/{transaction.flutterwave_transaction_id}/verify", 
                headers=headers
            )
            
            response_data = response.json()
            
            if response.status_code != 200 or not response_data.get('status') == 'success':
                transaction.status = PaymentTransaction.TransactionStatus.FAILED
                transaction.save()
                
                logger.error(f"Transaction Verification Failed: {response_data}")
                raise PaymentVerificationError(
                    message="Échec de la vérification de transaction",
                    error_code=response_data.get('message', 'VERIFICATION_FAILED')
                )
            
            # Mise à jour du statut
            data = response_data.get('data', {})
            transaction.status = (
                PaymentTransaction.TransactionStatus.SUCCESSFUL 
                if data.get('status') == 'successful' 
                else PaymentTransaction.TransactionStatus.FAILED
            )
            transaction.raw_response = response_data
            transaction.save()
            
            return {
                "transaction_reference": transaction.transaction_reference,
                "status": transaction.status,
                "amount": transaction.amount,
                "currency": transaction.currency
            }
        
        except PaymentTransaction.DoesNotExist:
            logger.error(f"Transaction non trouvée: {transaction_reference}")
            raise PaymentVerificationError(
                message="Transaction introuvable",
                error_code='TRANSACTION_NOT_FOUND',
                status_code=404
            )
        except requests.exceptions.RequestException as e:
            logger.exception("Erreur réseau lors de la vérification de transaction")
            raise PaymentVerificationError(str(e))
        except Exception as e:
            logger.exception("Erreur inattendue lors de la vérification de transaction")
            raise PaymentVerificationError(str(e))

    def refund_transaction(self, transaction, reason=None):
        """
        Effectue un remboursement pour une transaction donnée.
        
        Args:
            transaction (PaymentTransaction): Transaction à rembourser
            reason (str, optional): Raison du remboursement
        
        Returns:
            dict: Détails du remboursement
        """
        try:
            # Vérification des conditions de remboursement
            if transaction.status != PaymentTransaction.TransactionStatus.SUCCESSFUL:
                raise RefundException(
                    "Seules les transactions réussies peuvent être remboursées",
                    error_code='INVALID_REFUND_STATUS'
                )
            
            # Vérification du délai de remboursement (par exemple, moins de 30 jours)
            from django.utils import timezone
            import datetime
            
            if (timezone.now() - transaction.created_at) > datetime.timedelta(days=30):
                raise RefundException(
                    "Délai de remboursement dépassé",
                    error_code='REFUND_TIMEOUT'
                )
            
            # Préparation de la requête de remboursement
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "id": transaction.flutterwave_transaction_id,
                "amount": float(transaction.amount),
                "reason": reason or "Remboursement standard"
            }
            
            response = requests.post(
                f"{self.base_url}/transactions/refund", 
                json=payload, 
                headers=headers
            )
            
            response_data = response.json()
            
            # Gestion de la réponse
            if response.status_code != 200 or not response_data.get('status') == 'success':
                logger.error(f"Refund Failed: {response_data}")
                raise RefundException(
                    message="Échec du remboursement",
                    error_code=response_data.get('message', 'REFUND_FAILED')
                )
            
            # Mise à jour du statut de la transaction
            transaction.status = PaymentTransaction.TransactionStatus.REFUNDED
            transaction.raw_response = response_data
            transaction.save()
            
            return {
                "transaction_reference": transaction.transaction_reference,
                "refund_status": "SUCCESSFUL",
                "amount": transaction.amount,
                "currency": transaction.currency
            }
        
        except requests.exceptions.RequestException as e:
            logger.exception("Erreur réseau lors du remboursement")
            raise RefundException(str(e))
        except Exception as e:
            logger.exception("Erreur inattendue lors du remboursement")
            raise RefundException(str(e))
