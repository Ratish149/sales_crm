from django.core.management.base import BaseCommand
from tenants.models import Domain

class Command(BaseCommand):
    help = "Update domain names from .nepdora.baliyoventures.com to .nepdora.com"

    def handle(self, *args, **options):
        old_suffix = ".nepdora.baliyoventures.com"
        new_suffix = ".nepdora.com"
        
        domains = Domain.objects.filter(domain__icontains=old_suffix)
        updated_count = 0
        
        for domain_obj in domains:
            old_domain = domain_obj.domain
            if old_suffix in old_domain:
                new_domain = old_domain.replace(old_suffix, new_suffix)
                domain_obj.domain = new_domain
                domain_obj.save()
                self.stdout.write(self.style.SUCCESS(f"Updated: {old_domain} -> {new_domain}"))
                updated_count += 1
        
        if updated_count == 0:
            self.stdout.write(self.style.WARNING("No domains found matching the pattern."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} domain(s)."))
