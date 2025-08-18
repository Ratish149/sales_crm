from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid

# Create your models here.


class StoreProfile(models.Model):
    store_name = models.CharField(max_length=255)
    store_address = models.CharField(max_length=255, null=True, blank=True)
    store_number = models.CharField(max_length=255, null=True, blank=True)
    logo = models.URLField(null=True, blank=True)
    business_category = models.CharField(max_length=255, null=True, blank=True)
    facebook_url = models.CharField(max_length=255, null=True, blank=True)
    whatsapp_number = models.CharField(max_length=255, null=True, blank=True)
    instagram_url = models.CharField(max_length=255, null=True, blank=True)
    twitter_url = models.CharField(max_length=255, null=True, blank=True)
    tiktok_url = models.CharField(max_length=255, null=True, blank=True)
    document_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    phone_number = models.CharField(max_length=255, null=True, blank=True)

    def delete(self, *args, **kwargs):
        store = self.store
        super().delete(*args, **kwargs)
        # After user is deleted, check if store has any users left
        if store and not store.users.exists():
            store.delete()

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
