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

Supplementary information logged in Sentry
------------------------------------------

`collective.sentry` will create automatically a Sentry tag `instance_name`
which is derived from the buildout part name of the related instance.  An
additional tag `project` can be configured (optional) if you set the
environment variable `DSN_PROJECT`.  This allows you introduce an additional
tag for filtering, if needed.


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
