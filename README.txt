collective.sentry
=================

Sentry integration with Zope.

Requirements
------------

* Plone 5.2 (tested)
* Python 3.6+ (tested)

Installation
------------

Add `collective.sentry` to your buildout and re-run buildout. 

Configuration
-------------

Configure the Sentry DSN by setting the environment variable `SENTRY_DSN` inside your shell configuration or using buildout::

    [instance]
    environment-vars +=
        SENTRY_DSN https://......


Repository
----------

https://github.com/collective/collective.sentry

Licence
-------

- GPL2 - GNU Public License 2
- based on `raven.contrib.zope`: BSD


Author
------

ZOPYX/Andreas Jung, info@zopyx.com

`collective.sentry` has been developed as part of a Plone 5.2 migration project and it
sponsored by the University Gent.
