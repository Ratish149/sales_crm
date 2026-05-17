from django.db import models

from sales_crm.utils.s3bucket import PublicMediaStorage

# Create your models here.


class Gallery(models.Model):
    image = models.FileField(
        upload_to="gallery/images/", blank=True, null=True, storage=PublicMediaStorage()
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.image.url
