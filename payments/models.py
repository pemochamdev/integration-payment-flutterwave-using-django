from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class PaymentTransaction(models.Model):
    class TransactionStatus(models.TextChoices):
        INITIATED = 'INITIATED', _('Transaction Initiée')
        PENDING = 'PENDING', _('En Attente')
        SUCCESSFUL = 'SUCCESSFUL', _('Succès')
        FAILED = 'FAILED', _('Échec')
        REFUNDED = 'REFUNDED', _('Remboursé')

    class PaymentMethod(models.TextChoices):
        CARD = 'CARD', _('Carte Bancaire')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Virement Bancaire')
        MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money')
        USSD = 'USSD', _('USSD')

    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='payment_transactions',
        null=True,
        verbose_name=_('Utilisateur')
    )
    
    transaction_reference = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name=_('Référence Transaction')
    )
    
    flutterwave_transaction_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name=_('ID Transaction Flutterwave')
    )
    
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name=_('Montant')
    )
    
    currency = models.CharField(
        max_length=5, 
        default='USD', 
        verbose_name=_('Devise')
    )
    
    status = models.CharField(
        max_length=20, 
        choices=TransactionStatus.choices, 
        default=TransactionStatus.INITIATED,
        verbose_name=_('Statut')
    )
    
    payment_method = models.CharField(
        max_length=20, 
        choices=PaymentMethod.choices, 
        null=True, 
        blank=True,
        verbose_name=_('Méthode de Paiement')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_('Date de Création')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('Date de Mise à Jour')
    )
    
    customer_email = models.EmailField(
        verbose_name=_('Email Client'),
        null=True,
        blank=True
    )
    
    raw_response = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name=_('Réponse Brute')
    )
    
    def __str__(self):
        return f"{self.transaction_reference} - {self.status}"
    
    class Meta:
        verbose_name = _('Transaction de Paiement')
        verbose_name_plural = _('Transactions de Paiement')
        ordering = ['-created_at']
