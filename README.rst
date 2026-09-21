collective.sentry
=================

Sentry integration with Zope.

Quick start (zero config)
-------------------------

Install ``collective.sentry`` alongside your Zope/Plone instance and set::

    SENTRY_DSN=https://<key>@<host>/<project-id>

Optional environment variables:

- ``SENTRY_ENVIRONMENT`` — the environment tag (e.g. ``production``).
- ``SENTRY_PROJECT`` — set as tag ``project`` on every event.
- ``SENTRY_DISABLE`` — set to disable Sentry entirely.
- ``SENTRY_INTEGRATIONS`` — comma-separated dotted names of extra
  sentry-sdk integration classes (instantiated without arguments).
- ``SENTRY_MAX_LENGTH`` — maps to sentry-sdk's ``max_value_length``;
  unset keeps the SDK default.
- ``SENTRY_OPTIONAL`` — deprecated, ignored (a missing DSN just disables
  reporting).

In Plone the package is picked up automatically (z3c.autoinclude). On
plain Zope, import the package once at startup, e.g. from the WSGI
module::

    import collective.sentry  # noqa: F401

Own initialization (filtering etc.)
-----------------------------------

The env-var bootstrap steps aside when the SDK is already initialized, so
you can call ``sentry_sdk.init()`` yourself — for example to filter
scanner noise with ``before_send``, which since 2.0 belongs to you::

    import sentry_sdk
    from collective.sentry import ZopeIntegration

    def drop_scanner_noise(event, hint):
        # your filtering logic
        return event

    sentry_sdk.init(
        dsn="...",
        integrations=[ZopeIntegration()],
        before_send=drop_scanner_noise,
        ignore_errors=[KeyboardInterrupt],
    )

Run this before Zope loads the package ZCML (policy package module level,
or a paste filter in ``wsgi.ini``).

What gets reported
------------------

Unhandled publisher exceptions (via ``IPubFailure``) and ``logging``
errors, enriched per request with form data, cookies, lazy items, request
info and the authenticated user (email included when the user has PAS
properties, i.e. always in Plone). Passwords are filtered. Exception
types listed as ignored in the site's ``error_log`` are not reported.

Migrating from 1.x
------------------

- ``before_send`` is no longer occupied by this package; wrappers around
  ``collective.sentry.error_handler.before_send`` can be replaced by a
  plain ``before_send`` passed to your own ``sentry_sdk.init()``.
- ``collective.sentry.error_handler`` is deprecated (works, warns).
- ``SENTRY_INTEGRATIONS`` works again (it was silently broken since
  1.x/2022).
- ``SENTRY_MAX_LENGTH`` now only applies when explicitly set.
- ``plone.api`` is no longer a dependency; plain Zope 5 is supported.
- Transaction names are now the request path — review Sentry alert rules
  that filter on transaction.
- The deprecated ``error_handler.before_send`` shim only enriches — the
  ``error_log`` ignore check moved to the capture path (relevant only if
  you call the shim directly).
- ``extra["request"]["headers"]`` now contains proper header names
  (``HTTP_*`` transformed, non-header environ keys dropped, sensitive
  headers filtered) instead of the raw WSGI environ.
