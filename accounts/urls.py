from django.urls import path

from .views import (
    AcceptInvitationView,
    ChangePasswordView,
    CompleteOnboardingView,
    CustomSignupView,
    CustomVerifyEmailView,
    InvitationCreateView,
    RequestPasswordResetAPIView,
    ResendEmailVerificationView,
    ResendInvitationView,
    ResetPasswordConfirmAPIView,
    StoreProfileDetailView,
    StoreProfileView,
    UserDeleteAPIView,
    UserListDestroyAPIView,
    UserUpdateAPIView,
    UserWithStoresListAPIView,
    UseTemplateView,
    UserDataAPIView,
)

urlpatterns = [
    path("signup/", CustomSignupView.as_view(), name="signup"),
    path("verify-email/", CustomVerifyEmailView.as_view(), name="verify-email"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path(
        "resend-verification/",
        ResendEmailVerificationView.as_view(),
        name="resend-email-verification",
    ),
    path("invite/", InvitationCreateView.as_view(), name="invite-user"),
    path("invite/accept/", AcceptInvitationView.as_view(), name="accept-invite"),
    path(
        "invite/resend/<int:invitation_id>/",
        ResendInvitationView.as_view(),
        name="resend-invite",
    ),
    path("store-profile/", StoreProfileView.as_view(), name="store-profile"),
    path(
        "store-profile/me/",
        StoreProfileDetailView.as_view(),
        name="store-profile-detail",
    ),
    path("users/", UserWithStoresListAPIView.as_view(), name="users-with-stores"),
    path("users/me/", UserUpdateAPIView.as_view(), name="user-me"),
    path(
        "complete-onboarding/",
        CompleteOnboardingView.as_view(),
        name="complete-onboarding",
    ),
    path("user-lists/", UserListDestroyAPIView.as_view(), name="user-list"),
    path("user-lists/<int:id>/", UserDeleteAPIView.as_view(), name="user-delete"),
    path(
        "reset-password-request/",
        RequestPasswordResetAPIView.as_view(),
        name="reset-password-request",
    ),
    path(
        "reset-password-confirm/",
        ResetPasswordConfirmAPIView.as_view(),
        name="reset-password-confirm",
    ),
    path("templates/use/", UseTemplateView.as_view(), name="use-template"),
    path("user-data/", UserDataAPIView.as_view(), name="user-data"),
]
