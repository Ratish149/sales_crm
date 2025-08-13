from django.db import models

# Create your models here.


class Website(models.Model):
    user = models.ForeignKey('accounts.CustomUser',
                             on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    auto_create_schema = True

    def __str__(self):
        return self.name
