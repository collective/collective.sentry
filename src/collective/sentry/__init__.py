"""collective.sentry: sentry_sdk integration for Zope/Plone."""

from collective.sentry.bootstrap import initialize_from_environ
from collective.sentry.integration import ZopeIntegration  # noqa: F401

initialize_from_environ()
