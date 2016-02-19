#!/bin/bash

echo "Restarting gunicorn for {GUNICORN_FILE} server"

systemctl restart {GUNICORN_FILE}
