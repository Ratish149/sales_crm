from django.db import models

# Create your models here.


class TeamMember(models.Model):
    order = models.IntegerField(blank=True)
    name = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=200, blank=True)
    photo = models.FileField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    email = models.CharField(max_length=200, blank=True, null=True)
    facebook = models.URLField(max_length=200, blank=True, null=True)
    instagram = models.URLField(max_length=200, blank=True, null=True)
    linkedin = models.URLField(max_length=200, blank=True, null=True)
    twitter = models.URLField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ('order', 'name',)
