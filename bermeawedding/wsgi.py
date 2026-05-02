"""
WSGI config for bermeawedding project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bermeawedding.settings')

application = get_wsgi_application()
