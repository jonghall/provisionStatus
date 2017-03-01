#!/usr/bin/env bash

if [ -z "$VCAP_APP_PORT" ];
then SERVER_PORT=5000;
else SERVER_PORT="$VCAP_APP_PORT";
fi
echo port is------------------- $SERVER_PORT
python3.4 manage.py syncdb --noinput
gunicorn provisionStatus.wsgi --workers 3 --timeout 120
