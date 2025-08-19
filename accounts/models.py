from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# Create your models here.


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
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    sub_domain = models.CharField(max_length=255, null=True, blank=True)

    def is_owner_of(self, store):
        return self == store.owner

    def has_perm_in_store(self, store, required_role):
        """
        Check if user has required permission in the given store.
        Permission hierarchy: owner > admin > editor > viewer
        """
        role_weights = {'owner': 4, 'admin': 3, 'editor': 2, 'viewer': 1}
        user_role = self.role if self in store.users.all() else None

        if not user_role:
            return False

        return role_weights[user_role] >= role_weights[required_role]

    def __str__(self):
        return self.email


class StoreProfile(models.Model):
    owner = models.ForeignKey(
        'CustomUser', on_delete=models.CASCADE, related_name='owned_stores', null=True, blank=True)
    users = models.ManyToManyField(
        'CustomUser', related_name='stores', blank=True)
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

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        # Add the owner to the store's users if not already added
        if is_new and self.owner_id:
            self.users.add(self.owner)

    def __str__(self):
        return self.store_name or f"Store {self.id}"


class Invitation(models.Model):
    email = models.EmailField()
    store = models.ForeignKey(
        StoreProfile, on_delete=models.CASCADE, related_name='invitations', null=True, blank=True)
    invited_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')
    role = models.CharField(max_length=10, choices=CustomUser.ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('email', 'store')

    def accept(self, user):
        """Accept the invitation and add user to the store"""
        if self.accepted:
            return False

        self.accepted = True
        self.save()

        # Add user to store's users if not already added
        if user not in self.store.users.all():
            self.store.users.add(user)

        # If this is the first user (owner), ensure they have the owner role
        if self.store.owner == user:
            user.role = 'owner'
            user.save()

        return True

    def __str__(self):
        return f"Invitation for {self.email} to {self.store.store_name}"
