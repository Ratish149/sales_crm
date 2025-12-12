from tenants.models import Client, Domain

# Create a default tenant
default_tenant = Client.objects.create(
    name="Default Tenant",
    schema_name="public",  # or any other schema name you prefer
)

# Create a domain for the tenant
domain = Domain.objects.create(
    domain="pscow0g48c0k04o8kookgk8w.52.230.96.168.sslip.io",
    tenant=default_tenant,
    is_primary=True,
)
