from django.apps import AppConfig


class FacebookConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facebook'
    
    def ready(self):
        import facebook.signals
        return super().ready()
