from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.conf import settings


class Client(TenantMixin):
    name = models.CharField(max_length=100)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_on = models.DateField(auto_now_add=True)

    auto_create_schema = True  # Required for automatic schema creation


class Domain(DomainMixin):
    pass
