import os, sys, time

from fabric.api import *
from fabric.contrib.files import exists
from fabric.context_managers import cd

env.deploy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deploy')
env.config_dir = os.path.join(env.deploy_dir, 'config')

def check_dirs():
    sys.stdout.write('deploy_dir: %s\n' % env.get('deploy_dir', 'Not set'))
    sys.stdout.write('config_dir: %s\n' % env.get('config_dir', 'Not set'))
    sys.stdout.write('users_dir: %s\n' % env.get('users_dir', 'Not set'))
    sys.stdout.write('site_config_dir: %s\n' % env.get('site_config_dir', 'Not set'))
    sys.stdout.write('respoitory: %s\n' % env.get('repository', 'Not set'))

def check_terminal():
    run('echo $TERM', pty=True)

def create_users():
    '''
    Creates users for all usernames listed in the USERS variable. Each user
    must have an authorized_keys file available in order to be created.

    This function will always execute as the root, and should only be run on
    new servers.
    '''
    prev_env_user = env.user
    require('users', 'default_password', 'users_dir')
    for user in env.users:
        # Only create a user if we have a valid authorized_keys file for them.
        if os.path.exists(os.path.join(env.users_dir, user, '.ssh', 'authorized_keys')):
            run('useradd -m %(user)s -g sudo -s /bin/bash;'
                'echo "%(user)s:%(password)s" | sudo chpasswd;'
                'passwd -e %(user)s' % {'user':user, 'password':env.default_password}, pty=True)
            local('tar cvfz %(user)s.tar.gz -C %(users_dir)s %(user)s' % {
                'users_dir': env.users_dir,
                'user': user,
            })
            put('%s.tar.gz' % user, '/tmp/')
            local('rm %s.tar.gz' % user)
            run('tar zxf /tmp/%(user)s.tar.gz -C /home;'
                'rm /tmp/%(user)s.tar.gz;'
                'chown -R %(user)s:sudo /home/%(user)s;'
                'chmod -R 700 /home/%(user)s/.ssh;'
                'chmod -R 600 /home/%(user)s/.ssh/authorized_keys;' % {'user': user}, pty=True)
    env.user = prev_env_user

def configure_ssh():
    '''
    Copies our master sshd_config file to the server which disables root login
    and otherwise secures ssh connections.
    '''
    require('config_dir')
    put(os.path.join(env.config_dir, 'ssh', 'sshd_config'), '/tmp/sshd_config')
    with cd('/etc/ssh/'):
        sudo('mv /tmp/sshd_config ./sshd_config;'
            'chmod 622 ./sshd_config;'
            'chown root:root ./sshd_config', pty=True)
    sudo('/etc/init.d/ssh restart', pty=True)

def configure_firewall():
    ''' Installs and configures UFW. '''
    sudo('apt-get install -y ufw;'
        'ufw default deny incoming;'
        'ufw default allow outgoing;'
        'ufw limit OpenSSH;'
        'ufw allow www;'
        'echo y | ufw enable', pty=True)

def configure_fail2ban():
    ''' Installs and configures Fail2Ban. '''
    require('config_dir')
    put(os.path.join(env.config_dir, 'fail2ban', 'jail.conf'), '/tmp/jail.conf')
    sudo('apt-get install -y fail2ban;'
        'mv /tmp/jail.conf /etc/fail2ban/jail.conf;', pty=True)

def configure_unattended_upgrades():
    ''' Installs and configures "unattended-upgrades". '''
    require('config_dir')
    put(os.path.join(env.config_dir, 'apt', '10periodic'), '/tmp/10periodic')
    put(os.path.join(env.config_dir, 'apt', '50unattended-upgrades'), '/tmp/50unattended-upgrades')
    sudo('apt-get install -y unattended-upgrades;'
        'mv /tmp/10periodic /etc/apt/apt.conf.d/10periodic;'
        'mv /tmp/50unattended-upgrades /etc/apt/apt.conf.d/50unattended-upgrades;', pty=True)

def configure_motd():
    ''' Configures Paul's special custom MOTD. '''
    require('config_dir')
    put(os.path.join(env.config_dir, 'update-motd.d', '00-header'), '/tmp/00-header')
    put(os.path.join(env.config_dir, 'update-motd.d', '80-who'), '/tmp/80-who')
    put(os.path.join(env.config_dir, 'update-motd.d', '99-footer'), '/tmp/99-footer')
    sudo('rm -rf /etc/update-motd.d/*;'
        'mv /tmp/00-header /etc/update-motd.d/00-header;'
        'mv /tmp/80-who /etc/update-motd.d/80-who;'
        'mv /tmp/99-footer /etc/update-motd.d/99-footer;', pty=True)

def install_system_packages():
    ''' Install a full set of everything we want on the server. '''
    packages = set((
        'ntp',
        'emacs',
        'libxml2-dev',
        'python-setuptools',
        'python-imaging',
        'python-lxml',
        'python-pylibmc',
        'git-core',
        'python-dev',
        'python-psycopg2',
        'memcached',
        'nginx',
        'postgresql',
    ))
    if env.get('extra_packages', []):
        packages = packages.union(set(env.extra_packages))
    sudo('apt-get install -y python-software-properties', pty=True) # Required for add-apt-repository
    sudo('add-apt-repository ppa:nginx/stable;') # Add nginx's PPA
    sudo('apt-get update -y', pty=True)
    sudo('apt-get upgrade -y', pty=True)
    sudo('apt-get install -y %s' % " ".join(packages), pty=True)
    sudo('easy_install pip')
    sudo('pip install virtualenv')
    sudo('pip install uwsgi')

def create_dirs():
    ''' Creates standard set of directories (media, static, sites). '''
    require('domain')
    with cd('%(path)s' % env):
        if not exists('%(domain)s' % env, use_sudo=True):
            sudo('mkdir %(domain)s' % env)
        sudo('chown -R root:www-data ./%(domain)s; chmod -R 700 ./%(domain)s' % env)
        with cd('%(domain)s' % env):
            if not exists('./media', use_sudo=True):
                sudo('mkdir ./media;')
            # Media should be read + write for www-data
            sudo('chown -R root:www-data ./media; chmod -R 770 ./media')
            if not exists('./static', use_sudo=True):
                sudo('mkdir ./static;')
            # Static should be read only for www-data
            sudo('chown -R root:www-data ./static; chmod -R 750 ./static')
            if not exists('./site', use_sudo=True):
                sudo('mkdir ./site;')
            # Site files generally are no-access, .pyc files will be compiled
            # with permissions for www-data read + execute.
            sudo('chown -R root:www-data ./site; chmod -R 750 ./site')
            sudo('chmod -R 750 ./site')
            sudo('chmod 750 .')

def configure_db():
    ''' Configure postgresql with standard config files.'''
    sudo('/etc/init.d/postgresql stop')
    put(os.path.join(env.config_dir, 'postgresql', 'postgresql.conf'), '/tmp/postgresql.conf')
    put(os.path.join(env.config_dir, 'postgresql', 'pg_hba.conf'), '/tmp/pg_hba.conf')
    sudo('mv /tmp/postgresql.conf /etc/postgresql/8.4/main/postgresql.conf;'
        'chown postgres:postgres /etc/postgresql/8.4/main/postgresql.conf')
    sudo('mv /tmp/pg_hba.conf /etc/postgresql/8.4/main/pg_hba.conf;'
        'chown postgres:postgres /etc/postgresql/8.4/main/pg_hba.conf')
    sudo('/etc/init.d/postgresql start')

def create_db():
    require('db_name')
    sudo('createdb %(db_name)s' % env, user="postgres")

def remove_db():
    require('db_name')
    sudo('dropdb %(db_name)s' % env, user="postgres")

def remove_db_user(db_user):
    sudo('psql -c "DROP ROLE %s;"' % db_user, user="postgres")

def create_db_user(db_user, db_pass):
    sudo('psql -c "CREATE USER %s WITH ENCRYPTED PASSWORD \'%s\'"' % (db_user, db_pass), user="postgres")
    sudo('psql -c "CREATE DATABASE %s WITH OWNER %s"' % (db_user, db_user), user='postgres')

def backup_db():
    ''' Take a database backup with pg_dumpall and download it. '''
    require('backup_dir')
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    sudo('pg_dumpall -l valhalla | gzip > /tmp/db_%s.sql.gz' % timestamp, user="postgres")
    if not os.path.exists(env['backup_dir']):
        os.mkdir(env['backup_dir'])
    get('/tmp/db_%s.sql.gz' % timestamp, os.path.join(env['backup_dir'], 'db_%s.sql.gz' % timestamp))
    sudo('rm /tmp/db_%s.sql.gz' % timestamp)

def configure_nginx():
    ''' Upload nginx and uwsgi config files and reload nginx. '''
    require('config_dir')
    if exists('/etc/nginx/sites-enabled/default', use_sudo=True):
        sudo('rm /etc/nginx/sites-enabled/default')
    sudo('mkdir /var/log/nginx/emperor;'
        'chown -R www-data:adm /var/log/nginx;'
        'chmod -R 640 /var/log/nginx;'
        'mkdir /etc/nginx/emperor;'
        'touch /etc/nginx/emperor/fastrouter_webserver.sock;'
        'chown -R root:www-data /etc/nginx/emperor;'
        'chmod -R 770 /etc/nginx/emperor;')
    put(os.path.join(env.config_dir, 'nginx', 'uwsgi.conf'), '/tmp/uwsgi.conf')
    sudo('mv /tmp/uwsgi.conf /etc/init/uwsgi.conf; chown root:root /etc/nginx/nginx.conf; chmod 644 /etc/init/uwsgi.conf')
    put(os.path.join(env.config_dir, 'nginx', 'nginx.base.conf'), '/tmp/nginx.base.conf')
    sudo('mv /tmp/nginx.base.conf /etc/nginx/nginx.base.conf; chmod 644 /etc/nginx/nginx.base.conf')
    put(os.path.join(env.config_dir, 'nginx', 'nginx.conf'), '/tmp/nginx.conf')
    sudo('mv /tmp/nginx.conf /etc/nginx/nginx.conf;'
        'chmod 644 /etc/nginx/nginx.conf;'
        'service nginx start;'
        'service nginx reload;'
        'initctl start uwsgi;')

def reload_webserver():
    sudo('service nginx reload')

def reload_app():
    require('domain')
    sudo('touch %(path)s/%(domain)s/site/uwsgi.ini' % env)

def install_site_files():
    ''' Default implementation uploads an archive from current project directory. '''
    require('domain', 'repository')
    local('cd %(repository)s; git archive --format=tar master | gzip > %(domain)s.tar.gz' % env)
    put('%(repository)s%(domain)s.tar.gz' % env, '/tmp/%(domain)s.tar.gz' % env)
    local('rm %(repository)s%(domain)s.tar.gz'  % env)
    sudo('rm -rf %(path)s/%(domain)s/site/*;'
        'tar zxf /tmp/%(domain)s.tar.gz -C %(path)s/%(domain)s/site/;'
        'rm /tmp/%(domain)s.tar.gz;' % env)
    create_dirs() # Sets correct permissions

def install_site_conf():
    require('domain', 'site_config_dir')
    put(os.path.join(env.site_config_dir, 'nginx', 'uwsgi.ini'), '/tmp/uwsgi.ini')
    sudo('mv /tmp/uwsgi.ini %(path)s/%(domain)s/site/uwsgi.ini;'
        'chown -R root:www-data %(path)s/%(domain)s/site/uwsgi.ini;'
        'chmod 640 %(path)s/%(domain)s/site/uwsgi.ini;' % env)
    put(os.path.join(env.site_config_dir, 'nginx', 'nginx.conf'), '/tmp/nginx.conf')
    sudo('mv /tmp/nginx.conf %(path)s/%(domain)s/site/nginx.conf;'
        'chown -R root:www-data %(path)s/%(domain)s/site/nginx.conf;'
        'chmod 640 %(path)s/%(domain)s/site/nginx.conf' % env)
    sudo('service nginx reload')

def deploy():
    ''' Creates a clean install of a site. Does not destroy user data. '''
    require('domain', 'repository')
    with cd('%(path)s' % env):
        # Delete everything but the media directory
        sudo('rm -rf %(domain)s/static' % env)
        sudo('rm -rf %(domain)s/site' % env)
    create_dirs()
    install_site_files()
    with cd('%(path)s/%(domain)s' % env):
        sudo('virtualenv site' % env)
        with cd('site'):
            sudo('source bin/activate; pip install -r requirements.txt' % env)
            sudo('chown -R root:www-data .')
    install_site_conf()
    compress()
    collectstatic()

def update():
    require('domain', 'repository')
    install_site_files()
    with cd('%(path)s/%(domain)s' % env):
        sudo('virtualenv site' % env)
        with cd('site'):
            sudo('source bin/activate; pip install -r requirements.txt' % env)
            sudo('chown -R root:www-data .')
    install_site_conf()
    compress()
    collectstatic()

def destroy():
    require('domain')
    sudo('rm -rf %(path)s/%(domain)s' % env)

def compile():
    sudo('python -m compileall -q -f %(path)s/%(domain)s/site' % env)
    sudo('find %(path)s/%(domain)s/site -type f -name "*.pyc" -exec chmod 555 {} \;' % env)

def syncdb():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s/site' % env):
        sudo('source bin/activate; %(app_name)s/manage.py syncdb --noinput' % env)

def migrate():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s/site' % env):
        sudo('source bin/activate; %(app_name)s/manage.py migrate' % env)

def compress():
    if env.get('compress', False):
        require('domain', 'app_name')
        with cd('%(path)s/%(domain)s/site' % env):
            sudo('source bin/activate; %(app_name)s/manage.py compress' % env)

def collectstatic():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s/site' % env):
        sudo('source bin/activate;'
            '%(app_name)s/manage.py collectstatic --noinput;'
            'chmod -R 750 %(path)s/%(domain)s/static;'
            'chown -R root:www-data %(path)s/%(domain)s/static;' % env)

def loaddata(file):
    require('domain', 'app_name')
    put(file, '/tmp/loaddata.json')
    with cd('%(path)s/%(domain)s/site' % env):
        sudo('source bin/activate; %(app_name)s/manage.py loaddata /tmp/loaddata.json' % env)
    sudo('rm /tmp/loaddata.json')

def rebuild_index():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s/site' % env):
        sudo('source bin/activate; %(app_name)s/manage.py rebuild_index --noinput' % env)
        sudo('chown -R root:www-data %(app_name)s; chmod -R 750 %(app_name)s' % env)
        if exists('./%(app_name)s/_whoosh/' % env, use_sudo=True):
            sudo('chmod -R 770 ./%(app_name)s/_whoosh/' % env)

def update_index():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s/site' % env):
        sudo('source bin/activate; %(app_name)s/manage.py update_index' % env)


def new_server():
    create_users()
    configure_ssh()
    configure_firewall()
    configure_fail2ban()
    configure_unattended_upgrades()
    configure_motd()
    install_system_packages()
    configure_db()
    create_db()
    configure_nginx()
