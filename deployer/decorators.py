from functools import wraps

from fabric.api import *

__all__ = ('require_site',)

def require_site(f):
    @wraps(f)
    def check_site(site=None, *args, **kwargs):
        if site:
            env.site = site
        require('site')
        return f(*args, **kwargs)
    return check_site
