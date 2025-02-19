# Myriad Dashboard

Supported distribution: debian 12. Other Distributions should work as well, given equivalent dependencies are installed.

## production & staging setup:
* set timezone: `timedatectl set-timezone Europe/Berlin` (or other one, dependending where you are)
* install required packages:
* `apt install nginx uwsgi uwsgi-plugin-python3`
* `apt install --no-install-recommends -y python3 python3-pip python3-venv python3-mysqldb gdal-bin postgis`
* `adduser myriad`
* run as myriad user:
  ```bash
  python3 -m venv venv # create venv for django runtime
  source venv/bin/activate # activate venv
  echo "cd && source venv/bin/activate" >> .bashrc # activate it on every login
  pip install django numpy django-crispy-forms ruff djlint crispy-bootstrap5 django-htmx django-cotton django-template-partials pandas openpyxl fiona
  ```
* add `www-data` into `myriad` group and vice versa: `adduser myriad www-data ; adduser www-data myriad`
* allow read access for group: `chmod 750 /home/myriad`
* create `/etc/uwsgi/apps-available/myriad.ini` and link to `apps-enabled`:
  ```ini
  [uwsgi]
  socket     = /home/myriad/uwsgi.sock
  chmod-socket = 664
  chdir      = /home/myriad/myriad-app
  wsgi-file  = dashboard/wsgi.py

  master     = true
  processes  = 2
  threads    = 2
  http-websockets = true

  uid        = myriad
  gid        = myriad

  vacuum     = true

  plugins    = python3

  buffer-size= 16384

  virtualenv = /home/myriad/venv
  ```
* create `/etc/nginx/snippets/uwsgi_params`:
  ```
  uwsgi_param  QUERY_STRING       $query_string;
  uwsgi_param  REQUEST_METHOD     $request_method;
  uwsgi_param  CONTENT_TYPE       $content_type;
  uwsgi_param  CONTENT_LENGTH     $content_length;

  uwsgi_param  REQUEST_URI        $request_uri;
  uwsgi_param  PATH_INFO          $document_uri;
  uwsgi_param  DOCUMENT_ROOT      $document_root;
  uwsgi_param  SERVER_PROTOCOL    $server_protocol;
  uwsgi_param  REQUEST_SCHEME     $scheme;
  uwsgi_param  HTTPS              $https if_not_empty;

  uwsgi_param  REMOTE_ADDR        $remote_addr;
  uwsgi_param  REMOTE_PORT        $remote_port;
  uwsgi_param  SERVER_PORT        $server_port;
  uwsgi_param  SERVER_NAME        $server_name;
  ```
* setup `/etc/nginx/sites-available/www.example.com` (replaces `default`), link to `sites-enabled`, comment out https settings. Replace `www.example.com` with the domain of your choice of course:
  ```
  server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name www.example.com;

    root /var/www/www.example.com;

    # enforce https
    return 301 https://$host$request_uri;

    location ^~ /.well-known/ {
      root          /var/www/;
      autoindex     on;
      access_log    off;
      log_not_found off;
      auth_basic    off;
    }
  }

  server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    ssl_certificate /etc/nginx/certs/www.example.com.cer;
    ssl_certificate_key /etc/nginx/certs/www.example.com.key;
    ssl_dhparam /etc/nginx/certs/dhparam-2048.pem;

    server_name www.example.com;
    root /var/www/www.example.com;

    client_max_body_size 100M;

    location /static {
      root /var/www/www.example.com;
    }

    location /media {
      root /var/www/www.example.com;
    }

    location / {
      include snippets/uwsgi_params;
      uwsgi_pass unix:///home/myriad/uwsgi.sock;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;

      # add_header 'referrer-policy' 'strict-origin-when-cross-origin';
    }

    location ^~ /.well-known/ {
      root            /var/www/;
      autoindex       on;
      access_log      off;
      log_not_found   off;
      auth_basic      off;
    }
  }
  ```
* create web directory and chown to `myriad` user:
  ```bash
  mkdir /var/www/www.example.com
  chown myriad:myriad /var/www/www.example.com
  ```
* create app directory: `mkdir /home/myriad/myriad-app ; chown myriad:myriad /home/myriad/myriad-app/`
* copy `myriad/settings.py.template` to `/home/myriad/myriad-app/settings.py` and set everything up for "productive use"
* install and set up postgres:
  ```bash
  apt install postgresql postgresql-postgis
  sudo -u postgres bash
  createuser myriad
  createdb -O myriad myriad
  psql # enter psotgres
  \c myriad; # switch to newly created database
  CREATE EXTENSION postgis; # make sure to load the extension
  ```
* set up letsencrypt (start in `/root` directory, comment out https first for nginx):
  ```bash
  apt install git
  git clone https://github.com/acmesh-official/acme.sh.git
  cd acme.sh
  ./acme.sh --install -d admin@example.com
  # <log out and log in again>
  acme.sh --set-default-ca --server letsencrypt

  mkdir /etc/nginx/certs/

  acme.sh --issue --force -w /var/www \
    -d www.example.com

  acme.sh --install-cert --force -d www.example.com \
    --key-file       /etc/nginx/certs/www.example.com.key  \
    --fullchain-file /etc/nginx/certs/www.example.com.cer \
    --reloadcmd     "service nginx force-reload"
  ```
* finish nginx settings
  ```bash
  openssl dhparam -out /etc/nginx/certs/dhparam-2048.pem 2048
  cd  /etc/nginx/certs/
  ```
* un-comment `/etc/nginx/sites-available/www.example.com` and run `nginx -s reload`
* add `/home/myriad/reload_uwsgi.sh` with `chmod 755`:
  ```bash
  #!/bin/bash

  systemctl restart uwsgi
  ```
* add `/etc/sudoers.d/deploy-trigger`:
  ```bash
  ALL ALL=NOPASSWD: /home/myriad/reload_uwsgi.sh
  ```
