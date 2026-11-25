#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [[ -n "${DJANGO_BOOTSTRAP_ADMIN_USERNAME:-}" || -n "${DJANGO_BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
    if [[ -z "${DJANGO_BOOTSTRAP_ADMIN_USERNAME:-}" || -z "${DJANGO_BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
        echo "Both bootstrap admin environment variables must be set." >&2
        exit 1
    fi

    python manage.py shell -c '
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_BOOTSTRAP_ADMIN_USERNAME"]
password = os.environ["DJANGO_BOOTSTRAP_ADMIN_PASSWORD"]
user = User.objects.filter(username=username).first()

if user is None:
    User.objects.create_superuser(username=username, email="", password=password)
    print("Bootstrap admin created.")
elif not user.is_superuser or not user.check_password(password):
    raise SystemExit("Bootstrap username already exists; choose a different username.")
else:
    print("Bootstrap admin already exists.")
'
fi
