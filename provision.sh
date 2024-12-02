#!/bin/bash

npm install

python -m venv venv

venv/bin/pip install `cat pip_packages.txt`

source venv/bin/activate

python3 ./manage.py collectstatic
