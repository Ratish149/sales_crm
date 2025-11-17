from tenants.models import Client, Domain

# Create a default tenant
default_tenant = Client.objects.create(
    name="Default Tenant",
    schema_name="public",  # or any other schema name you prefer
)

# Create a domain for the tenant
domain = Domain.objects.create(
    domain="127.0.0.1", tenant=default_tenant, is_primary=True
)
