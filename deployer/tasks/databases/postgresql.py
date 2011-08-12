import os
from fabric.api import *
from fabric.context_managers import cd

def install_db():
    sudo('apt-get install -y postgresql')

def configure_db():
    sudo('/etc/init.d/postgresql stop')
    put(os.path.join(env.config_dir, 'postgresql', 'postgresql.conf'), '/tmp/postgresql.conf')
    put(os.path.join(env.config_dir, 'postgresql', 'pg_hba.conf'), '/tmp/pg_hba.conf')
    sudo('mv /tmp/postgresql.conf /etc/postgresql/8.4/main/postgresql.conf;'
        'chown postgres:postgres /etc/postgresql/8.4/main/postgresql.conf')
    sudo('mv /tmp/pg_hba.conf /etc/postgresql/8.4/main/pg_hba.conf;'
        'chown postgres:postgres /etc/postgresql/8.4/main/pg_hba.conf')
    sudo('/etc/init.d/postgresql start')
