"""sentry_sdk integration for the Zope WSGI publisher. Zope-only."""

from collective.sentry.capture import on_pub_failure
from collective.sentry.extraction import request_event_processor
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.logging import ignore_logger
from zope.component import provideHandler
from ZPublisher import WSGIPublisher
from ZPublisher.interfaces import IPubFailure

import functools
import sentry_sdk


class ZopeIntegration(Integration):
    identifier = "zope"

    @staticmethod
    def setup_once():
        if getattr(WSGIPublisher.publish_module, "_sentry_wrapped", False):
            return

        original = WSGIPublisher.publish_module

        @functools.wraps(original)
        def sentry_publish_module(environ, start_response, **kw):
            with sentry_sdk.isolation_scope() as scope:
                scope.clear_breadcrumbs()
                scope.add_event_processor(request_event_processor)
                scope.set_transaction_name(environ.get("PATH_INFO", "/"), source="url")
                return original(environ, start_response, **kw)

        sentry_publish_module._sentry_wrapped = True
        WSGIPublisher.publish_module = sentry_publish_module

        provideHandler(on_pub_failure, (IPubFailure,))
        # The publisher logs failures to Zope.SiteErrorLog; without this the
        # logging integration would report every error twice.
        ignore_logger("Zope.SiteErrorLog")
