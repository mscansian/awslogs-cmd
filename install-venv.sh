#!/bin/bash

if [ -d "venv" ]; then
    echo "virtualenv directory exists. nothing to do"
    exit 0
fi

virtualenv -p python3 venv
venv/bin/pip3 install boto3 pytz
