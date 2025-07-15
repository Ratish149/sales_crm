from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid

# Create your models here.


class StoreProfile(models.Model):
    store_name = models.CharField(max_length=255, null=True, blank=True)
    store_address = models.CharField(max_length=255, null=True, blank=True)
    store_number = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.store_name or f"Store {self.id}"


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    )
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default='viewer')
    store = models.ForeignKey(
        StoreProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='users')

    def __str__(self):
        return self.email


class Invitation(models.Model):
    email = models.EmailField()
    store = models.ForeignKey(
        StoreProfile, on_delete=models.CASCADE, related_name='invitations', null=True, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    role = models.CharField(max_length=10, choices=CustomUser.ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite to {self.email} for {self.store}"
