#!/usr/bin/env python3
"""Print a fresh Django SECRET_KEY suitable for the .env file.

Tries Django's helper first; falls back to a stdlib-only generator if
Django isn't importable (e.g. running this from a clean shell with no
venv activated).
"""

try:
    from django.core.management.utils import get_random_secret_key
    print(get_random_secret_key())
except ImportError:
    import secrets
    import string
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    print(''.join(secrets.choice(chars) for _ in range(50)))
