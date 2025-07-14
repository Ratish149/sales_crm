from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    store_name=models.CharField(max_length=255, null=True, blank=True)
    email=models.EmailField(unique=True)

    def __str__(self):
        return self.email
    
class StoreProfile(models.Model):
    user=models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    store_address=models.CharField(max_length=255, null=True, blank=True)
    store_number=models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.user.email