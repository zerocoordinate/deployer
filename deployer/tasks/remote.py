import os, sys, time

from fabric.api import *
from fabric.contrib.files import exists
from fabric.context_managers import cd

from ..utils import yesno, call_backend_task

#hacky
env.deploy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'deploy')
env.config_dir = os.path.join(env.deploy_dir, 'config')

def site_exists():
    if exists('%(path)s/%(domain)s' %env):
        sys.stdout.write('INSTALLED: The site "%(domain)s" is installed on this server.\n' % env)
    else:
        sys.stdout.write('NOT INSTALLED: The site "%(domain)s" is not installed on this server.\n' % env)

@runs_once
def generate_keys():
    ''' Create ssh keys for the root user on the server. '''
    sudo('chmod 700 /root/.ssh;'
         'ssh-keygen -q -t rsa -P "" -f /root/.ssh/id_rsa')

def create_users(user=None):
    '''
    Creates users for all usernames listed in the USERS variable. Each user
    must have an authorized_keys file available in order to be created.

    This function will always execute as the root, and should only be run on
    new servers.
    '''
    prev_env_user = env.user
    require('users', 'default_password', 'users_dir')
    if user is not None:
        env.users = (user,)
    for user in env.users:
        # Only create a user if we have a valid authorized_keys file for them.
        if os.path.exists(os.path.join(env.users_dir, user, '.ssh', 'authorized_keys')):
            if exists('/home/%s' % user):
                sys.stdout.write('Remote user "%s" already exists. Proceeding to next user.\n' % user)
                continue
            sudo('useradd -m %(user)s -g sudo -G admin -s /bin/bash;'
                'echo "%(user)s:%(password)s" | sudo chpasswd;'
                'passwd -e %(user)s' % {'user':user, 'password':env.default_password}, pty=True)
            local('tar cvfz %(user)s.tar.gz -C %(users_dir)s %(user)s' % {
                'users_dir': env.users_dir,
                'user': user,
            })
            put('%s.tar.gz' % user, '/tmp/')
            local('rm %s.tar.gz' % user)
            sudo('tar zxf /tmp/%(user)s.tar.gz -C /home;'
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
    ))
    if env.get('extra_packages', []):
        packages = packages.union(set(env.extra_packages))
    sudo('apt-get install -y python-software-properties', pty=True) # Required for add-apt-repository
    sudo('apt-get update -y', pty=True)
    sudo('apt-get upgrade -y', pty=True)
    sudo('apt-get install -y %s' % " ".join(packages), pty=True)
    sudo('easy_install pip')
    sudo('pip install virtualenv')
    install_LESS()

def install_LESS():
    sudo("apt-get install -y python-software-properties curl;"
         "yes|add-apt-repository ppa:chris-lea/node.js;"
         "apt-get update;"
         "apt-get install -y nodejs npm;"
         "npm install less -g;")

def install_varnish():
    put(os.path.join(env.config_dir, 'varnish', 'default.vcl'), '/tmp/default.vcl')
    sudo('curl http://repo.varnish-cache.org/debian/GPG-key.txt | apt-key add -;'
         'echo "deb http://repo.varnish-cache.org/ubuntu/ lucid varnish-3.0" >> /etc/apt/sources.list;'
         'apt-get update;'
         'apt-get install -y varnish;'
         'mv /tmp/default.vcl /etc/varnish/default.vcl;')

def start_varnish():
    sudo('varnishd -f /etc/varnish/default.vcl -s malloc,128M -T 127.0.0.1:2000;')

def stop_varnish():
    sudo('pkill varnish;')

def restart_varnish():
    stop_varnish()
    start_varnish()

def install_databases():
    call_backend_task('databases', 'install_db')

def install_webservers():
    call_backend_task('webservers', 'install_webserver')

def create_dirs():
    ''' Creates standard set of directories (media, static, sites). '''
    require('domain')
    with cd('%(path)s' % env):
        if not exists('%(domain)s' % env, use_sudo=True):
            sudo('mkdir %(domain)s' % env)
        with cd('%(domain)s' % env):
            if not exists('./media', use_sudo=True):
                sudo('mkdir ./media;')
            if not exists('./static', use_sudo=True):
                sudo('mkdir ./static;')
            if not exists('./site', use_sudo=True):
                sudo('mkdir ./site;')
    repair_permissions()

def repair_permissions():
    ''' Restores permissions for a site to their correct state. '''
    sudo('cd %(path)s;'
         # Restore proper ownership.
         'chown -Rf root:www-data %(domain)s;'
         # Start with a baseline of no permissions for anyone but root.
         'chmod -R 700 %(domain)s;'
         # Start group needs write permission on the root for the domain.
         'chmod 750 %(domain)s;'
         # Media should be read + write for www-data
         'chmod -Rf 770 %(domain)s/media;'
         # Static needs read + execute for www-data (not sure why it needs execute, but it does)
         'chmod -Rf 750 %(domain)s/static;' #FIXME -- This isn't read-only
         # Site dir (python and config files) should be read + execute
         'chmod -Rf 750 %(domain)s/site;'
         # Virtualenv dirs need to be executable
         'chmod -Rf 750 %(domain)s/lib %(domain)s/src %(domain)s/bin;'
         'chmod 750 %(domain)s;' % env)

def configure_databases():
    ''' Configure database with standard config files. Currently supports PostgreSQL with optional PostGIS support.'''
    require('databases')
    call_backend_task('databases', 'configure_db')

def create_db(db_user, db_name):
    ''' Creates a database with the given name and owner. '''
    call_backend_task('databases', 'create_db', db_user, db_name)

def remove_db():
    ''' Drops a database. '''
    require('db_name')
    call_backend_task('databases', 'remove_db')

def remove_db_user(db_user):
    ''' Deletes a database user. '''
    call_backend_task('databases', 'remove_db_user', db_user)

def create_db_user(db_user, db_pass):
    ''' Create a database user with the given username and password. '''
    call_backend_task('databases', 'create_db_user', db_user, db_pass)

def backup_db():
    ''' Take a database backup and download it. '''
    call_backend_task('databases', 'backup_db')

def configure_webservers():
    ''' Upload necessary files for webserver configuration. '''
    require('config_dir')
    call_backend_task('webservers', 'configure_webserver')

def restart_webservers():
    call_backend_task('webservers', 'restart_webserver')
    restart_varnish()

def install_site_files():
    ''' Default implementation uploads an archive from current project directory. '''
    require('domain', 'repository')
    local('cd %(repository)s; git archive --format=tar master | gzip > %(domain)s.tar.gz' % env)
    put('%(repository)s%(domain)s.tar.gz' % env, '/tmp/%(domain)s.tar.gz' % env)
    local('rm %(repository)s%(domain)s.tar.gz'  % env)
    sudo('rm -rf %(path)s/%(domain)s/site/*;'
         'tar zxf /tmp/%(domain)s.tar.gz -C %(path)s/%(domain)s/site/;'
         'rm /tmp/%(domain)s.tar.gz;' % env)
    repair_permissions() # Sets correct permissions

def install_requirements():
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate;'
             'bin/pip install -r site/requirements.txt;')
    repair_permissions()

def install_site_conf():
    require('domain', 'site_config_dir')
    call_backend_task('webservers', 'install_site_conf')

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
        sudo('virtualenv . --system-site-packages')
        with cd('site'):
            sudo('chown -R root:www-data .')
    install_requirements()
    install_site_conf()
    collectstatic()
    compress()
    repair_permissions()
    restart_webservers()

def update(reqs='yes'):
    require('domain', 'repository')
    install_site_files()
    sudo('chown -R root:www-data %(path)s/%(domain)s/site' % env)
    if yesno(reqs):
        install_requirements()
    install_site_conf()
    collectstatic()
    compress()
    repair_permissions()
    restart_webservers()

def destroy():
    ''' Removes ALL site files from the remote server. DANGER. '''
    require('domain')
    with settings(abort_on_prompts=False):
        proceed = prompt('**Warning** This will delete all site files on disk including uploaded media. Continue? [y/N]: ', default='n', validate=yesno)
        if not proceed:
            abort('Canceled by user input.')
    sudo('rm -rf %(path)s/%(domain)s' % env)

def compile():
    ''' Pre-compile all Python files and set approriate permissions (Experimental) '''
    sudo('python -m compileall -q -f %(path)s/%(domain)s/site' % env)
    sudo('find %(path)s/%(domain)s/site -type f -name "*.pyc" -exec chmod 555 {} \;' % env)

def syncdb():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('%(path)s/%(domain)s/bin/django-admin.py syncdb --noinput --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)

def migrate():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('%(path)s/%(domain)s/bin/django-admin.py migrate --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)

def compress():
    if env.get('compress', False):
        require('domain', 'app_name')
        with cd('%(path)s/%(domain)s' % env):
            sudo('cd site/%(app_name)s; %(path)s/%(domain)s/bin/django-admin.py compress --pythonpath=`pwd` --settings=%(settings_module)s' % env)

def collectstatic():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('%(path)s/%(domain)s/bin/django-admin.py collectstatic --noinput --pythonpath=site/%(app_name)s --settings=%(settings_module)s;'
            'chmod -R 750 %(path)s/%(domain)s/static;'
            'chown -R root:www-data %(path)s/%(domain)s/static;' % env)

def loaddata(file):
    require('domain', 'app_name')
    put(file, '/tmp/loaddata.json')
    with cd('%(path)s/%(domain)s' % env):
        sudo('%(path)s/%(domain)s/bin/django-admin.py loaddata /tmp/loaddata.json --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)
    sudo('rm /tmp/loaddata.json')

def rebuild_index():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('%(path)s/%(domain)s/bin/django-admin.py rebuild_index --noinput --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)
        sudo('chown -R root:www-data site/%(app_name)s;'
             'chmod -R 750 site/%(app_name)s' % env)
        if exists('site/%(app_name)s/_whoosh/' % env, use_sudo=True):
            sudo('chmod -R 770 site/%(app_name)s/_whoosh/' % env)

def update_index():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('%(path)s/%(domain)s/bin/django-admin.py update_index --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)


def new_server():
    require('databases')
    create_users()
    configure_ssh()
    configure_firewall()
    configure_fail2ban()
    configure_unattended_upgrades()
    configure_motd()
    install_system_packages()
    install_databases()
    install_webservers()
    install_varnish()
    configure_databases()
    configure_webservers()
    restart_varnish()


def maintenance(state=None, branch="master"):
    ''' Enables or disables a maintenance page for the site. '''
    env.branch = branch
    if state == 'on':
        if exists('/etc/nginx/sites-enabled/maintenance', use_sudo=True):
            with settings(abort_on_prompts=False):
                proceed = prompt('It appears that maintenance mode is already on. Continue? [y/N]: ', default='n', validate=yesno)
                if not proceed:
                    abort('Canceled by user input.')
        put('configs/nginx/maintenance', '/etc/nginx/sites-available/maintenance', use_sudo=True)
        if not exists('/etc/nginx/sites-enabled.old', use_sudo=True):
            sudo('mkdir /etc/nginx/sites-enabled.old')
        sudo('mv -f /etc/nginx/sites-enabled/* /etc/nginx/sites-enabled.old/;'
             'ln -sf /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/maintenance;')
    elif state == 'off':
        if not exists('/etc/nginx/sites-enabled/maintenance', use_sudo=True):
            with settings(abort_on_prompts=False):
                proceed = prompt('It appears that maintenance mode is already off. Continue? [y/N]: ', default='n', validate=yesno)
                if not proceed:
                    abort('Canceled by user input.')
        sudo('mv -f /etc/nginx/sites-enabled.old/* /etc/nginx/sites-enabled/;'
             'rm -f /etc/nginx/sites-enabled/maintenance;')
    else:
        abort('Please specify either "on" or "off".')
    sudo('service nginx reload')
