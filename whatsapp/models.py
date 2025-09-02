from django.db import models
from solo.models import SingletonModel
# Create your models here.


class Whatsapp(SingletonModel):
    message = models.TextField()
    phone_number = models.CharField(max_length=15)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.phone_number
