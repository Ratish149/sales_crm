from django.db import models
from solo.models import SingletonModel


# Create your models here.
class GoogleAnalytic(SingletonModel):
    measurement_id = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return "Google Analytic"
