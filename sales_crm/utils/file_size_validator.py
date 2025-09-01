from django.core.exceptions import ValidationError

# Create your models here.


def file_size(value):  # add this to some file where you can import it from
    limit = 500 * 1024  # 500 KB
    if value.size > limit:
        raise ValidationError('File too large. Size should not exceed 500 KB.')
