import os
from fabric.api import *
from fabric.context_managers import cd

from .postgresql import remove_db, remove_db_user, create_db_user, backup_db
from .postgresql import configure_db as configure_postgresql

def install_db():
    packages = (
        'postgresql',
        'binutils',
        'gdal-bin',
        'postgresql-8.4-postgis',
        'postgresql-server-dev-8.4',
        'libgeoip1',
        'python-gdal',
    )
    sudo('apt-get install -y %s;' % " ".join(packages))

def configure_db():
    configure_postgresql()
    create_spatialdb_template()

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

def create_db(db_user, db_name):
    ''' Creates a PostgreSQL database. '''
    sudo('psql -c "CREATE DATABASE %s WITH OWNER %s TEMPLATE template_postgis"' % (db_name, db_user), user='postgres')
