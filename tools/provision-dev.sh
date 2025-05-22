#!/bin/bash

npm ci

npm run build-styles

python3 -m venv venv

venv/bin/pip install `cat requirements.txt`

venv/bin/pip-licenses --format=json --with-license-file --no-license-path > dashboard/py-oss-licenses.json

source venv/bin/activate

python3 ./manage.py export_openapi_schema --api data.api.api_v1 --output data/schema.json --indent 2 --sorted

# https://openapi-ts.dev/cli
npx openapi-typescript data/schema.json -o data/types/api.ts --make-paths-enum --root-types --root-types-no-schema-prefix

npm run build-styles
npm run build