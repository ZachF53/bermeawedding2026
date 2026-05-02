from django.conf import settings


def wedding_info(request):
    return {'WEDDING': getattr(settings, 'WEDDING', {})}
