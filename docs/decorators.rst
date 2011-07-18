.. module:: deployer.decorators

==========
Decorators
==========

.. function:: require_site([site])

    Ensures that either the ``env.site`` variable is set, or that a ``site``
    argument is passed as the first argument to the decorated function. Exits
    gracefully if neither of these conditions are met.
