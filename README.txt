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
environment variable `SENTRY_PROJECT`.  This allows you introduce an additional
tag for filtering, if needed.

Another option for filtering is `SENTRY_ENVIRONMENT`, useful to differentiate 
between e.g. staging vs production 
(https://docs.sentry.io/enriching-error-data/environments/?platform=python).


Optional activation
---------------------
By default, if you install `collective.sentry` along you eggs, the instance start will crash if you do not configure `SENTRY_DSN`.
But sometime, you have multiple environments where you want that the product to be loaded, without doing anything under the hood (same conf for dev & prod, but no sentry on dev).
To enable this behavior, add `SENTRY_OPTIONAL=1` to your environment variables.

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
