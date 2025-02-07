from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments.views import PaymentTransactionViewSet

router = DefaultRouter()
router.register(r'transactions', PaymentTransactionViewSet, basename='payment-transaction')

urlpatterns = [
    path('', include(router.urls)),
]
