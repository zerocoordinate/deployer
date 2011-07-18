===========
Environment
===========

Fabric relies heavily on the the ``env`` variable to hold shared global state.
In keeping with tradition, the Deployer defines quite a few properties
(in addition to the standard ones, some of which are documented here for
convenience) that can be set on the environment variable.

    **path**

    The base path to your environment on the server. example: ``env.path = '/srv'``

    **hosts**

    The various host strings to which your application should be deployed.
    example: ``env.hosts = ['127.0.0.1']``

    **roledefs**

    Named roles for sets of hosts to define which tasks should be carried out
    on which machines. example: ``env.roledefs = {'app': ['50.56.101.61'],}``

    **domain**

    The domain name associated with the site being deployed. This is used in
    various places to separate different sites deployed to the same server.
    example: ``env.domain = 'sportslabhq.com'``

    **users**

    A tuple of usernames which correspond to user directories (see below)
    which should be installed by default on a new server. example: ``env.users = ('gabriel',)``

    **default_password**

    A temporary password to be set for user accounts created on the server.
    This password will require the user to change it upon first login. example:
    ``env.default_password = 'chang3m3'``

    .. note::

        While this is not ideally secure, it is made relatively secure by
        the fact that the password-only login is disabled so a user can only log in
        and change their password from the default if they the correct SSH key.

    **users_dir**

    The path to a directory containing user directories (see below). example:
    ``env.users_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users')``

    **site_config_dir**

    The path to a directory containing configuration files for the site (as
    opposed to the server).
    example: ``env.site_config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')``

    **repository**

    The path to a git repository from which to push the site code. example:
    ``env.repository = '/srv/my_virtualenv/my_project/'``

    **app_name**

    The name of the Django app directory within your repository. This will
    generally be the directory which contains ``settings.py``. example:
    ``env.app_name = 'project'``

    **db_name**

    The name of the database which the site uses. example: ``env.db_name = 'sportslab'``

    **extra_packages**

    A python ``set`` of additional Ubuntu package names which should be
    installed during server setup. example:
    ``env.extra_packages = ('mercurial', 'libcairo2-dev', 'python-cairo', 'python-rsvg',)``
