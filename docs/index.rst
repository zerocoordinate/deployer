========
Deployer
========

.. module:: deployer

It configures servers. It deploys Django sites. It's amazing!

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

How to use it
=============

There are four main components to using the Deployer: the environment,
the pre-built tasks, your server configuration files, and your user directories.

See the sections below for specific information:

.. toctree::
   :maxdepth: 2

   environment
   tasks
   config_files
   user_dirs

Developing with The Deployer
============================

If the built-in tasks don't meet all your needs (and they probably won't), there
are also some handy extras available to help you write your own methods on top
of the Fabric API while still taking advantage of many of the benefits of The
Deployer.

.. toctree::
   :maxdepth: 2

   utils
   decorators
   context_managers
