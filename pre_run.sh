#!/bin/bash

# Run Django collectstatic and migrate
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Start the Django application
exec "$@"
