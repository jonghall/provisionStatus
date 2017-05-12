#!/usr/bin/env bash

if [ -z "$VCAP_APP_PORT" ];
then SERVER_PORT=5000;
else SERVER_PORT="$VCAP_APP_PORT";
fi
echo port is------------------- $SERVER_PORT

echo "------ Create database tables ------"
python manage.py migrate --noinput

echo "------ create default admin user ------"
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'user@gmail.com', 'password')" | python manage.py shell

echo "------ starting gunicorn &nbsp;------"
gunicorn provisionStatus.wsgi --workers 3 --timeout 120
