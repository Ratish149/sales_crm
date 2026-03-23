from django.db import models

# Create your models here.
from sales_crm.utils.s3bucket import PublicMediaStorage



class Testimonial(models.Model):
    name = models.CharField(max_length=255)
    designation = models.CharField(max_length=255, null=True, blank=True)
    image = models.FileField(upload_to='testimonial/',storage=PublicMediaStorage(), null=True, blank=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
