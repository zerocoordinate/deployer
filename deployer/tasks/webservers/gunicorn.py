import os
from fabric.api import *
from fabric.context_managers import cd

def install_webserver():
    pass

def configure_webserver():
    require('config_dir')
    put(os.path.join(env.config_dir, 'upstart', 'gunicorn.conf'), '/tmp/gunicorn.conf')
    put(os.path.join(env.config_dir, 'upstart', 'gsite.conf'), '/tmp/gsite.conf')
    sudo('mv /tmp/gunicorn.conf /etc/init/gunicorn.conf;'
         'mv /tmp/gsite.conf /etc/init/gsite.conf;'
         'chmod 755 /etc/init/gunicorn.conf;'
         'chown root:root /etc/init/gunicorn.conf;'
         'chmod 755 /etc/init/gsite.conf;'
         'chown root:root /etc/init/gsite.conf;')

def start_webserver():
    sudo('start gunicorn;')

def stop_webserver():
    sudo('stop gunicorn;')

def restart_webserver():
    stop_webserver()
    start_webserver()

def install_site_conf():
    put(os.path.join(env.site_config_dir, 'gunicorn', 'gunicorn.conf'), '/tmp/gunicorn.conf')
    sudo('mv /tmp/gunicorn.conf %(path)s/%(domain)s/site/gunicorn.conf;'
        'chown -R root:www-data %(path)s/%(domain)s/site/gunicorn.conf;'
        'chmod 750 %(path)s/%(domain)s/site/gunicorn.conf' % env)
    restart_webserver()
