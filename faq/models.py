from django.db import models

# Create your models here.


class FAQ(models.Model):
    question = models.TextField(max_length=500)
    answer = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question
