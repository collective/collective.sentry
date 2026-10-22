from collective.sentry.tests.utils import CapturingTransport
from collective.sentry.tests.utils import FakeRequest
from collective.sentry.tests.utils import reset_sentry
from zope.component import getGlobalSiteManager
from ZPublisher import WSGIPublisher
from ZPublisher.interfaces import IPubFailure

import contextlib
import sentry_sdk
import unittest


class TestSetupOnce(unittest.TestCase):
    def setUp(self):
        reset_sentry()
        self._orig_pubevents = WSGIPublisher.transaction_pubevents
        self.calls = []

        @contextlib.contextmanager
        def stub_pubevents(request, response, tm=None):
            self.calls.append(sentry_sdk.get_isolation_scope())
            yield

        WSGIPublisher.transaction_pubevents = stub_pubevents

    def tearDown(self):
        WSGIPublisher.transaction_pubevents = self._orig_pubevents
        from collective.sentry.capture import on_pub_failure

        getGlobalSiteManager().unregisterHandler(on_pub_failure, (IPubFailure,))
        reset_sentry()

    def _init(self):
        from collective.sentry.integration import ZopeIntegration

        sentry_sdk.init(
            dsn="https://x@example.com/1",
            transport=CapturingTransport(),
            default_integrations=False,
            integrations=[ZopeIntegration()],
        )

    def _request(self, path="/plone/some-view"):
        return FakeRequest(environ={"PATH_INFO": path, "REQUEST_METHOD": "GET"})

    def test_wraps_transaction_pubevents_once(self):
        self._init()
        wrapped = WSGIPublisher.transaction_pubevents
        self.assertTrue(getattr(wrapped, "_sentry_wrapped", False))
        reset_sentry()  # allows setup_once to run again
        self._init()
        self.assertIs(WSGIPublisher.transaction_pubevents, wrapped)

    def test_registers_pub_failure_handler(self):
        from collective.sentry.capture import on_pub_failure

        self._init()
        handlers = list(getGlobalSiteManager().registeredHandlers())
        self.assertIn(on_pub_failure, [h.handler for h in handlers])

    def test_request_gets_isolated_scope_and_transaction(self):
        self._init()
        outer = sentry_sdk.get_isolation_scope()
        with WSGIPublisher.transaction_pubevents(self._request(), None):
            inside = sentry_sdk.get_isolation_scope()
        inner = self.calls[0]
        self.assertIsNot(inner, outer)
        self.assertIs(inside, inner)
        self.assertEqual(inner._transaction, "/plone/some-view")
        self.assertIs(sentry_sdk.get_isolation_scope(), outer)
