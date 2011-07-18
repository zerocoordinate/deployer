from fabric.api import *

@runs_once
@hosts('localhost')
def check_env(key=None):
    with hide('stdout', 'stderr', 'running'):
        if key:
            puts('%s: %s\n' %(key, env[key]))
        else:
            for k, v in env.items():
                puts('%s: %s\n' %(k, v))

def check_dirs():
    sys.stdout.write('deploy_dir: %s\n' % env.get('deploy_dir', 'Not set'))
    sys.stdout.write('config_dir: %s\n' % env.get('config_dir', 'Not set'))
    sys.stdout.write('users_dir: %s\n' % env.get('users_dir', 'Not set'))
    sys.stdout.write('site_config_dir: %s\n' % env.get('site_config_dir', 'Not set'))
    sys.stdout.write('respoitory: %s\n' % env.get('repository', 'Not set'))

def check_terminal():
    run('echo $TERM', pty=True)
