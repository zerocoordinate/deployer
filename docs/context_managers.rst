.. module:: deployer.context_managers

================
Context Managers
================

.. function:: change_host(host)

    Used to switch to a different host for all tasks performed within the
    managed block. For example, the following code would execute the appropriate
    directory creation tasks for each host in your ``env.roledefs`` for a given
    ``role`` passed in as an argument::

    def makedirs(role):
        for host in env.roledefs[role]:
            with change_host(host):
                sudo('mkdir -p %(path)s' % env)
                set_permissions('%(path)s' % env)

    The context manager can be used as a standalone, or (more usefully) within
    a loop as demonstrated above.
