import django_filters

from .models import NepdoraVideo


class NepdoraVideoFilter(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(choices=NepdoraVideo.TYPE_CHOICES)

    class Meta:
        model = NepdoraVideo
        fields = ["type"]
