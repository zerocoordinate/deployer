===================
Configuration Files
===================

There are a few key configuration files which are needed in order to serve
sites via your webserver (currently nginx).

nginx.conf
==========

Located in ``[env.config_dir]/nginx``. Example::

    server {
        server_name example.com;
        listen 80;

        location /favicon.ico {
            root /srv/example.com/static/img;
            expires 1d;
        }

        location /media/ {
            root /srv/example.com;
            expires 1d;
        }

        location /static/ {
            root /srv/example.com;
            expires 1d;
        }

        location / {
            include uwsgi_params;
            uwsgi_pass unix:/tmp/example.com.uwsgi.sock;
        }
    }

uwsgi.ini
=========

Located in ``[env.config_dir]/nginx``. Example::

    [uwsgi]
    chdir = %dproject
    virtualenv = %d../
    master = true
    socket = /tmp/example.com.uwsgi.sock
    env = DJANGO_SETTINGS_MODULE=settings.production
    env = UWSGI=true
    module = django.core.handlers.wsgi:WSGIHandler()
