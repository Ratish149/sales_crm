from django.urls import path

from .views import (
    AcceptInvitationView,
    ChangePasswordView,
    CustomSignupView,
    CustomVerifyEmailView,
    DeleteUserAndSchemaView,
    InvitationCreateView,
    ResendEmailVerificationView,
    ResendInvitationView,
    StoreProfileDetailView,
    StoreProfileView,
    UserWithStoresListAPIView,
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
    path(
        "delete-account/<int:user_id>/",
        DeleteUserAndSchemaView.as_view(),
        name="delete-user-and-schema",
    ),
]
