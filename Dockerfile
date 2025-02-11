FROM debian:bookworm
WORKDIR /myriad-dashboard

COPY docker-uwsgi-conf.ini .

COPY ./ ./

RUN mkdir db
RUN mkdir run

RUN ln -s ../settings/settings.py dashboard/settings.py

RUN apt update
RUN apt-get -y upgrade
RUN apt install --no-install-recommends -y python3 python3-pip python3-venv python3-mysqldb wget python3-jwt python3-cryptography uwsgi uwsgi-plugin-python3
RUN pip install --break-system-packages `cat pip_packages.txt`

RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

CMD python3 manage.py migrate ; \
  python3 manage.py collectstatic --noinput ; \
  uwsgi docker-uwsgi-conf.ini
