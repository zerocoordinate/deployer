import os
from fabric.api import *
from fabric.context_managers import cd

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
    from .postgresql import configure_db as configure_postgresql
    configure_postgresql()
    create_spatialdb_template()
    create_db()

def create_db():
    ''' Creates a PostgreSQL database from the given template. '''
    require('db_name', 'db_template_string')
    if 'db_template' in env:
        env.db_template_string = '-T %(db_template)s' % env
    else:
        env.db_template_string = '-T template_postgis'
    sudo('createdb %(db_template_string)s %(db_name)s' % env, user="postgres")
