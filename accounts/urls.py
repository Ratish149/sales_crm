from django.urls import path
from .views import ChangePasswordView, ResendEmailVerificationView

urlpatterns = [
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('resend-verification/', ResendEmailVerificationView.as_view(),
         name='resend-email-verification'),

]
