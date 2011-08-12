import os
from fabric.api import *
from fabric.context_managers import cd

def install_webserver():
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate;'
             'pip install -E . gunicorn')

def configure_webserver():
    require('config_dir')
    put(os.path.join(env.config_dir, 'upstart', 'gunicorn.conf'), '/tmp/gunicorn.conf')
    put(os.path.join(env.config_dir, 'upstart', 'gsite.conf'), '/tmp/gsite.conf')
    sudo('mv /tmp/gunicorn.conf /etc/init.d/gunicorn.conf;'
         'mv /tmp/gsite.conf /etc/init.d/gsite.conf;'
         'chmod 755 /etc/init.d/gunicorn.conf;'
         'chown root:root /etc/init.d/gunicorn.conf;'
         'chmod 755 /etc/init.d/gsite.conf;'
         'chown root:root /etc/init.d/gsite.conf;')
    start_webserver()

def start_webserver():
    sudo('start gunicorn;')

def stop_webserver():
    sudo('stop gunicorn;')
