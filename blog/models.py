from django.db import models
from django.utils.text import slugify
from sales_crm.storage_backends import PublicMediaStorage
from sales_crm.utils.file_size_validator import file_size
# Create your models here.


class Blog(models.Model):
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField()
    thumbnail_image = models.FileField(
        upload_to='blog/images/', null=True, blank=True, storage=PublicMediaStorage(), validators=[file_size])
    thumbnail_image_alt_description = models.CharField(
        max_length=255, blank=True, null=True)
    time_to_read = models.CharField(max_length=255, null=True, blank=True)
    tags = models.ManyToManyField('Tags', related_name='blogs', blank=True)
    meta_title = models.CharField(max_length=255, null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('title', 'slug')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Tags(models.Model):
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
