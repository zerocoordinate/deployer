import os
from fabric.api import *
from fabric.contrib.files import exists

def install_webserver():
    sudo('apt-get install -y python-software-properties', pty=True) # Required for add-apt-repository
    sudo('add-apt-repository ppa:nginx/stable;') # Add nginx's PPA
    sudo('apt-get update -y', pty=True)
    sudo('apt-get upgrade -y', pty=True)
    sudo('apt-get install -y nginx', pty=True)
    #install_uwsgi()

def remove_default_site():
    if exists('/etc/nginx/sites-enabled/default', use_sudo=True):
        sudo('rm /etc/nginx/sites-enabled/default')

def install_uwsgi():
    sudo('pip install uwsgi')

def configure_uwsgi():
    ''' Sets up uwsgi in emperor mode. '''
    require('config_dir')
    remove_default_site()
    sudo('mkdir /var/log/nginx/emperor;'
        'mkdir /etc/nginx/emperor;'
        'touch /etc/nginx/emperor/fastrouter_webserver.sock;'
        'chown -R root:www-data /etc/nginx/emperor;'
        'chmod -R 770 /etc/nginx/emperor;')
    put(os.path.join(env.config_dir, 'nginx', 'uwsgi.conf'), '/tmp/uwsgi.conf')
    sudo('mv /tmp/uwsgi.conf /etc/init/uwsgi.conf;'
         'chmod 644 /etc/init/uwsgi.conf;'
         'initctl start uwsgi;')

def configure_nginx():
    require('config_dir')
    remove_default_site()
    put(os.path.join(env.config_dir, 'nginx', 'nginx.conf'), '/tmp/nginx.conf')
    sudo('chown -R www-data:adm /var/log/nginx;'
         'chmod -R 640 /var/log/nginx;'
         'mv /tmp/nginx.conf /etc/nginx/nginx.conf;'
         'chmod 644 /etc/nginx/nginx.conf;'
         'chown root:root /etc/nginx/nginx.conf;'
         'service nginx start;')
    reload_webserver()

def restart_webserver():
    sudo('service nginx reload')

def configure_webserver():
    #configure_uwsgi()
    configure_nginx()

def install_uwsgi_conf():
    put(os.path.join(env.site_config_dir, 'nginx', 'uwsgi.ini'), '/tmp/uwsgi.ini')
    sudo('mv /tmp/uwsgi.ini %(path)s/%(domain)s/site/uwsgi.ini;'
        'chown -R root:www-data %(path)s/%(domain)s/site/uwsgi.ini;'
        'chmod 640 %(path)s/%(domain)s/site/uwsgi.ini;' % env)

def install_site_conf():
    #install_uwsgi_conf()
    put(os.path.join(env.site_config_dir, 'nginx', 'nginx.conf'), '/tmp/nginx.conf')
    sudo('mv /tmp/nginx.conf %(path)s/%(domain)s/site/nginx.conf;'
        'chown -R root:www-data %(path)s/%(domain)s/site/nginx.conf;'
        'chmod 640 %(path)s/%(domain)s/site/nginx.conf' % env)
    reload_webserver()
