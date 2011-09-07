import os
from fabric.api import *
from fabric.context_managers import cd

def install_db():
    sudo('apt-get install -y spatialite-bin libspatialite-dev;'
         'cd /tmp;'
         'wget http://pysqlite.googlecode.com/files/pysqlite-2.6.0.tar.gz;'
         'tar xzf pysqlite-2.6.0.tar.gz;'
         'cd pysqlite-2.6.0;'
         'rm setup.cfg;')
    put(os.path.join(env.config_dir, 'pysqlite2', 'setup.cfg'), '/tmp/pysqlite-2.6.0/setup.cfg')
    sudo('cd /tmp/pysqlite-2.6.0;'
         'sudo python setup.py install;'
         'cd /tmp;'
         'rm -r pysqlite-2.6.0;'
         'rm pysqlite-2.6.0.tar.gz;')

def configure_db():
    pass

def create_db(db_user=None, db_name=None):
    ''' Creates a spatialite database from the default data. '''
    if db_name is not None:
        env['db_name'] = db_name
    require('db_name', 'app_name')
    put(os.path.join(env.config_dir, 'spatialite', 'init_spatialite-2.3.sql'), '/tmp/init_spatialite-2.3.sql')
    sudo('spatialite %(path)s/%(domain)s/site/%(app_name)s/%(db_name)s.db < /tmp/init_spatialite-2.3.sql;'
         'rm /tmp/init_spatialite-2.3.sql;' % env)

def remove_db():
    require('db_name', 'app_name')
    sudo('rm -f %(path)s/%(domain)s/site/%(app_name)s/%(db_name)s.db' % env)

def remove_db_user(db_user):
    raise NotImplementedError()

def create_db_user(db_user, db_pass):
    raise NotImplementedError()

def backup_db():
    ''' Take a database backup with pg_dumpall and download it. '''
    require('backup_dir', 'db_name', 'app_name')
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    db_path = "%(path)s/%(domain)s/site/%(app_name)s/%(db_name)s.db" % env
    sudo('%(db_path)s | gzip > /tmp/db_%s.db.gz' % (timestamp, db_path))
    if not os.path.exists(env['backup_dir']):
        os.mkdir(env['backup_dir'])
    get('/tmp/db_%s.db.gz' % timestamp, os.path.join(env['backup_dir'], 'db_%s.db.gz' % timestamp))
    sudo('rm /tmp/db_%s.db.gz' % timestamp)
