from django.db import models

# Create your models here.


class SiteModel(models.Model):
    user = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.CASCADE,null=True,blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
