import imp, os

from fabric.api import *

DEPLOYER_PATH = imp.find_module('deployer')[1]
_backends = {}

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
         'chmod -Rf %(perms)s %(path)s' % {'user': user,
                                           'group': group,
                                           'perms': perms,
                                           'path': path})

def load_backend(mod_name, backend_dir):
    backend_key = '.'.join((mod_name, backend_dir,))
    if not _backends.has_key(backend_key):
        search_path = os.path.join(DEPLOYER_PATH, "tasks", backend_dir)
        f, path, description = imp.find_module(mod_name, [search_path,])
        try:
            backend = imp.load_module(mod_name, f, path, description)
            _backends[backend_key] = backend
        except ImportError:
            abort('Error: Could not load the backend "%s".' % backend_name)
        finally:
            f.close()
    else:
        backend = _backends[backend_key]
    return backend

def call_backend_task(backend_type, task, *args, **kwargs):
    backends = list(env[backend_type]) # Ensure proper handling for list or string
    for backend_name in backends:
        backend = load_backend(backend_name, backend_type)
        getattr(backend, task)(*args, **kwargs)
