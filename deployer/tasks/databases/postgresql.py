import os
from fabric.api import *
from fabric.context_managers import cd

def install_db():
    sudo('apt-get install -y postgresql')

def configure_db():
    sudo('/etc/init.d/postgresql stop')
    put(os.path.join(env.config_dir, 'postgresql', 'postgresql.conf'), '/tmp/postgresql.conf')
    put(os.path.join(env.config_dir, 'postgresql', 'pg_hba.conf'), '/tmp/pg_hba.conf')
    sudo('mv /tmp/postgresql.conf /etc/postgresql/9.1/main/postgresql.conf;'
        'chown postgres:postgres /etc/postgresql/9.1/main/postgresql.conf')
    sudo('mv /tmp/pg_hba.conf /etc/postgresql/9.1/main/pg_hba.conf;'
        'chown postgres:postgres /etc/postgresql/9.1/main/pg_hba.conf')
    sudo('/etc/init.d/postgresql start')

def create_db(db_user, db_name):
    ''' Creates a PostgreSQL database from the given template. '''
    sudo('psql -c "CREATE DATABASE %s WITH OWNER %s"' % (db_name, db_user), user='postgres')

def remove_db():
    require('db_name')
    sudo('dropdb %(db_name)s' % env, user="postgres")

def remove_db_user(db_user):
    sudo('psql -c "DROP ROLE %s;"' % db_user, user="postgres")

def create_db_user(db_user, db_pass):
    sudo('psql -c "CREATE USER %s WITH ENCRYPTED PASSWORD \'%s\'"' % (db_user, db_pass), user="postgres")

def backup_db():
    ''' Take a database backup with pg_dumpall and download it. '''
    require('backup_dir')
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    sudo('pg_dumpall -l valhalla | gzip > /tmp/db_%s.sql.gz' % timestamp, user="postgres")
    if not os.path.exists(env['backup_dir']):
        os.mkdir(env['backup_dir'])
    get('/tmp/db_%s.sql.gz' % timestamp, os.path.join(env['backup_dir'], 'db_%s.sql.gz' % timestamp))
    sudo('rm /tmp/db_%s.sql.gz' % timestamp)
