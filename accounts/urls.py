from django.urls import path
from .views import ChangePasswordView, ResendEmailVerificationView, InvitationCreateView, AcceptInvitationView, StoreProfileView, StoreProfileDetailView

urlpatterns = [
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('resend-verification/', ResendEmailVerificationView.as_view(),
         name='resend-email-verification'),

    path('invite/', InvitationCreateView.as_view(), name='invite-user'),
    path('invite/accept/', AcceptInvitationView.as_view(), name='accept-invite'),

    path('store-profile/', StoreProfileView.as_view(), name='store-profile'),
    path('store-profile/me/', StoreProfileDetailView.as_view(),
         name='store-profile-detail'),
]
