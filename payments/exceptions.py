class PaymentException(Exception):
    """Exception de base pour les erreurs de paiement"""
    def __init__(self, message, error_code=None, status_code=400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class PaymentInitiationError(PaymentException):
    """Erreur lors de l'initiation du paiement"""
    def __init__(self, message, error_code='PAYMENT_INITIATION_FAILED'):
        super().__init__(message, error_code=error_code, status_code=400)

class PaymentVerificationError(PaymentException):
    """Erreur lors de la vérification du paiement"""
    def __init__(self, message, error_code='PAYMENT_VERIFICATION_FAILED'):
        super().__init__(message, error_code=error_code, status_code=404)
        
class RefundException(PaymentException):
    """Exception spécifique pour les erreurs de remboursement"""
    def __init__(self, message, error_code='REFUND_FAILED'):
        super().__init__(message, error_code=error_code, status_code=400)
