from fabric.api import *

def yesno(input):
    if input.lower() in ['y', 'yes',]:
        return True
    elif input.lower() in ['n', 'no']:
        return False
    else:
        raise ValueError('Please enter "y" or "n".')

def set_permissions(path, perms='775', user=None, group=None):
    if not user:
        require('user')
        user = env.user
    if not group:
        require('group')
        group = env.group
    sudo('chown -R %(user)s:%(group)s %(path)s;'
         'chmod -Rf %(perms)s %(path)s' % {'user': user, 'group': group, 'perms': perms, 'path': path})
