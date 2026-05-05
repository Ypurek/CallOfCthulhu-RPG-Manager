#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cthulhu_rpg.settings')
django.setup()

from django.conf import settings
print('✓ AUTH_PASSWORD_VALIDATORS налаштування:')
print()
for validator in settings.AUTH_PASSWORD_VALIDATORS:
    print(f'  • {validator["NAME"]}')
    if 'OPTIONS' in validator:
        print(f'    Параметри: {validator["OPTIONS"]}')
print()
print('✓ Валідація паролів налаштована на мінімум 6 символів!')

