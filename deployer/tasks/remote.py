import os, sys, time

from fabric.api import *
from fabric.contrib.files import exists
from fabric.context_managers import cd

from ..utils import yesno

#hacky
env.deploy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'deploy')
env.config_dir = os.path.join(env.deploy_dir, 'config')

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

def configure_databases():
    ''' Configure database with standard config files. Currently supports PostgreSQL with optional PostGIS support.'''
    require('databases')
    databases = list(env.databases) # Ensure proper handling for list or string
    if 'postgresql' in databases:
        from .databases.postgresql import configure_db
        configure_db()
    if 'postgis' in databases:
        from .databases.postgis import configure_db
        configure_db()

def create_spatialdb_template():
    ''' Runs the PostGIS spatial DB template script. '''
    put(os.path.join(env.deploy_dir, 'create_template_postgis-debian.sh'),
        '/tmp/', mirror_local_mode=True)
    try:
        sudo('/tmp/create_template_postgis-debian.sh', user='postgres')
    except:
        pass #FIXME -- Don't catch everything and do nothing! At least abort with a useful error.
    finally:
        run('rm -f /tmp/create_template_postgis-debian.sh')

def create_db():
    ''' Creates a PostgreSQL database from the given template. '''
    require('db_name')
    if 'db_template' in env:
        env.db_template_string = '-T %(db_template)s' % env
    else:
        env.db_template_string = '-T template_postgis'
    sudo('createdb %(db_template_string)s %(db_name)s' % env, user="postgres")

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

def configure_webserver():
    ''' Upload nginx and uwsgi config files and reload nginx. '''
    require('config_dir')

def reload_webserver():
    sudo('service nginx reload')

def install_LESS():
    sudo("apt-get install -y python-software-properties curl;"
         "add-apt-repository ppa:jerome-etienne/neoip;"
         "sudo apt-get update;"
         "sudo apt-get install -y nodejs;"
         "export skipclean=1;"
         "curl http://npmjs.org/install.sh | sudo -E sh;"
         "sudo npm install less -g;")

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

def install_requirements():
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate;'
             'pip install -E . -r site/requirements.txt' % env)

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
        sudo('virtualenv .')
        with cd('site'):
            sudo('chown -R root:www-data .')
    install_requirements()
    install_site_conf()
    collectstatic()
    compress()

def update(reqs='yes'):
    require('domain', 'repository')
    install_site_files()
    sudo('chown -R root:www-data %(path)s/%(domain)s/site' % env)
    if yesno(reqs):
        install_requirements()
    install_site_conf()
    collectstatic()
    compress()

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
        sudo('source bin/activate; bin/django-admin.py syncdb --noinput --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)

def migrate():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate; bin/django-admin.py migrate --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)

def compress():
    if env.get('compress', False):
        require('domain', 'app_name')
        with cd('%(path)s/%(domain)s' % env):
            sudo('source bin/activate; cd site/%(app_name)s; %(path)s/%(domain)s/bin/django-admin.py compress --pythonpath=`pwd` --settings=%(settings_module)s' % env)

def collectstatic():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate;'
            'bin/django-admin.py collectstatic --noinput --pythonpath=site/%(app_name)s --settings=%(settings_module)s;'
            'chmod -R 750 %(path)s/%(domain)s/static;'
            'chown -R root:www-data %(path)s/%(domain)s/static;' % env)

def loaddata(file):
    require('domain', 'app_name')
    put(file, '/tmp/loaddata.json')
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate; bin/django-admin.py loaddata /tmp/loaddata.json --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)
    sudo('rm /tmp/loaddata.json')

def rebuild_index():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate; bin/django-admin.py rebuild_index --noinput --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)
        sudo('chown -R root:www-data site/%(app_name)s;'
             'chmod -R 750 site/%(app_name)s' % env)
        if exists('site/%(app_name)s/_whoosh/' % env, use_sudo=True):
            sudo('chmod -R 770 site/%(app_name)s/_whoosh/' % env)

def update_index():
    require('domain', 'app_name')
    with cd('%(path)s/%(domain)s' % env):
        sudo('source bin/activate; bin/django-admin.py update_index --pythonpath=site/%(app_name)s --settings=%(settings_module)s' % env)


def new_server():
    require('databases')
    create_users()
    configure_ssh()
    configure_firewall()
    configure_fail2ban()
    configure_unattended_upgrades()
    configure_motd()
    install_system_packages()
    install_LESS()
    configure_db()
    configure_nginx()


def maintenance(state=None, branch="master"):
    ''' Enables or disables a maintenance page for the site. '''
    env.branch = branch
    if state == 'on':
        if exists('/etc/nginx/sites-enabled/maintenance', use_sudo=True):
            with settings(abort_on_prompts=False):
                proceed = prompt('It appears that maintenance mode is already on. Continue? [y/N]: ', default='n', validate=yesno)
                if not proceed:
                    abort('Canceled by user input.')
        with lcd('../itlabs/static'):
            local('git archive --format=tar %(branch)s | gzip > static.tar.gz' % env)
            put('static.tar.gz', '/tmp/maintenance.tar.gz')
            local('rm static.tar.gz')
            sudo('rm -rf %(path)s/maintenance;'
                 'mkdir %(path)s/maintenance;'
                 'tar zxf /tmp/maintenance.tar.gz -C %(path)s/maintenance;'
                 'chown -R %(user)s:%(group)s %(path)s/maintenance;'
                 'chmod -R 750 %(path)s/maintenance;'
                 'rm /tmp/maintenance.tar.gz;' % env)
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
