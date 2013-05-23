WSGI Manager
============

This is an early-stage project that can provision and deploy a Python WSGI app on Amazon EC2 from a remote repository in one step. It is mainly an exercise in learning Ansible.

It's as easy as running: ``fab launch:https://github.com/v13inc/mycoolrepo``.

Behind the scenes the servers are provisioned with Ansible, and use a combination of NGinx, UWSGI and supervisor as the stack.
