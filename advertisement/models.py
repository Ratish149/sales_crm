from django.db import models

# Create your models here.


class PopUp(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.FileField(upload_to='banners/', null=True, blank=True)
    disclaimer = models.TextField(blank=True, null=True)
    enabled_fields = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class PopUpForm(models.Model):
    popup = models.ForeignKey(PopUp, on_delete=models.CASCADE,
                              related_name='pop_up_form', null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
