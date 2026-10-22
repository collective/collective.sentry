"""sentry_sdk integration for the Zope WSGI publisher. Zope-only."""

from collective.sentry.capture import on_pub_failure
from collective.sentry.extraction import request_event_processor
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.logging import ignore_logger
from zope.component import provideHandler
from ZPublisher import WSGIPublisher
from ZPublisher.interfaces import IPubFailure

import contextlib
import functools
import sentry_sdk


class ZopeIntegration(Integration):
    identifier = "zope"

    @staticmethod
    def setup_once():
        if getattr(WSGIPublisher.transaction_pubevents, "_sentry_wrapped", False):
            return

        # Wrap transaction_pubevents, not publish_module: WSGI servers get
        # publish_module from Zope2.Startup.run.make_wsgi_app, which imports
        # it before ZCML (and with it this package) is loaded, so a patched
        # publish_module is never called. publish_module looks up
        # transaction_pubevents on every request, and it spans the whole
        # publishing attempt, including IPubFailure and the error view.
        original = WSGIPublisher.transaction_pubevents

        @contextlib.contextmanager
        @functools.wraps(original)
        def sentry_transaction_pubevents(request, response, *args, **kw):
            with sentry_sdk.isolation_scope() as scope:
                scope.clear_breadcrumbs()
                scope.add_event_processor(request_event_processor)
                scope.set_transaction_name(
                    request.environ.get("PATH_INFO", "/"), source="url"
                )
                with original(request, response, *args, **kw):
                    yield

        sentry_transaction_pubevents._sentry_wrapped = True
        WSGIPublisher.transaction_pubevents = sentry_transaction_pubevents

        provideHandler(on_pub_failure, (IPubFailure,))
        # The publisher logs failures to Zope.SiteErrorLog; without this the
        # logging integration would report every error twice.
        ignore_logger("Zope.SiteErrorLog")
