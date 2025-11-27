from django.db import models


# Create your models here.
class Video(models.Model):
    title = models.CharField(max_length=255,null=True,blank=True)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title if self.title else self.url
