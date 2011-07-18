========
Deployer
========

It builds servers. It deploys Django sites. It's amazing!

What is the Deployer?
=====================

We built the Deployer to make spinning up small Django
webapps trivial. By setting a few configuration variables it can take a bare
Ubuntu instance (a la Rackspace Cloud, Slicehost, or Amazon EC2) and have a
securely-configured, functional webserver running your app in a matter of
minutes.

**What Deployer is not**: This isn't meant to be a one-size fits all solution.
As we continue to develop it, one of the goals is to add more hooks to allow
customization of the process for your preferred OS, webserver, directory
structure, etc. For now, though, it's meant to take a very common deployment
pattern and make it easy, repeatable, and secure.

Everything Else
===============

Please take a look at the ``docs/`` directory for full details.
