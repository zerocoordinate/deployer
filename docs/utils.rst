.. module:: deployer.utils

=========
Utilities
=========

.. function:: yesno(input)

    Tests an input string for values indicating "yes" or "no" and returns
    ``True`` or ``False`` respectively.

.. function:: set_permissions(path, [perms='775', user=env.user, group=env.group])

    Sets permissions, user, and group on a file or a directory (recursive) using
    chmod and chown.
