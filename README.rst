===============
Zalando Kubectl
===============

.. image:: https://img.shields.io/pypi/dw/zalando-kubectl.svg
   :target: https://pypi.python.org/pypi/zalando-kubectl/
   :alt: PyPI Downloads

.. image:: https://img.shields.io/pypi/v/zalando-kubectl.svg
   :target: https://pypi.python.org/pypi/zalando-kubectl/
   :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/l/zalando-kubectl.svg
   :target: https://pypi.python.org/pypi/zalando-kubectl/
   :alt: License

Kubernetes CLI (kubectl) wrapper in Python with OAuth token authentication.

This wrapper script serves as a drop-in replacement for the ``kubectl`` binary:

* it downloads the current ``kubectl`` binary from Google
* it generates a new ``~/.kube/config`` with an OAuth Bearer token acquired via `zign`_.
* it passes through commands to the ``kubectl`` binary


Installation
============

Requires Python 3.4+.

.. code-block:: bash

    $ sudo pip3 install --upgrade zalando-kubectl

Usage
=====

.. code-block:: bash

    $ zalando-kubectl login https://my-api-server.example.org
    $ zalando-kubectl cluster-info

.. _zign: https://pypi.python.org/pypi/stups-zign
