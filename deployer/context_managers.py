from contextlib import contextmanager

from fabric.api import *

__all__ = ('change_host',)

@contextmanager
def change_host(host):
    prev_host = env.host_string
    env.host_string = host
    yield
    env.host_string = prev_host
