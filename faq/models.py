from django.db import models

# Create your models here.


class FAQCategory(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FAQ(models.Model):
    question = models.TextField(max_length=500)
    answer = models.TextField(max_length=1000)
    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.CASCADE,
        related_name="faqs",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question
    
    class Meta:
        unique_together = ('question', 'answer')
