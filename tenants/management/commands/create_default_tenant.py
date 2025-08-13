from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from tenants.models import Client, Domain
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates a default tenant with domain 127.0.0.1'

    def handle(self, *args, **options):
        try:
            # Create a superuser if one doesn't exist
            User = get_user_model()
            if not User.objects.exists():
                superuser = User.objects.create_superuser(
                    email='baliyo@admin.com',
                    password='123',
                    username='baliyo'
                )
            else:
                # Use the first superuser if one exists
                superuser = User.objects.filter(is_superuser=True).first()

            # Create a default tenant
            default_tenant = Client.objects.create(
                name='Default Tenant',
                schema_name='public',
                owner=superuser
            )

            # Create a domain for the tenant
            domain = Domain.objects.create(
                domain='nepdora.baliyoventures.com',
                tenant=default_tenant,
                is_primary=True
            )

            self.stdout.write(self.style.SUCCESS(
                'Successfully created default tenant and domain'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Error creating tenant: {str(e)}'))
