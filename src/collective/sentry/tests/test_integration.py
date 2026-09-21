from collective.sentry.tests.utils import CapturingTransport
from collective.sentry.tests.utils import reset_sentry
from zope.component import getGlobalSiteManager
from ZPublisher import WSGIPublisher
from ZPublisher.interfaces import IPubFailure

import sentry_sdk
import unittest


class TestSetupOnce(unittest.TestCase):
    def setUp(self):
        reset_sentry()
        self._orig = WSGIPublisher.publish_module
        self.calls = []

        def stub_publish(environ, start_response, **kw):
            scope = sentry_sdk.get_isolation_scope()
            self.calls.append(scope)
            return [b"ok"]

        WSGIPublisher.publish_module = stub_publish

    def tearDown(self):
        WSGIPublisher.publish_module = self._orig
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

    def test_wraps_publish_module_once(self):
        self._init()
        wrapped = WSGIPublisher.publish_module
        self.assertTrue(getattr(wrapped, "_sentry_wrapped", False))
        reset_sentry()  # allows setup_once to run again
        self._init()
        self.assertIs(WSGIPublisher.publish_module, wrapped)

    def test_registers_pub_failure_handler(self):
        from collective.sentry.capture import on_pub_failure

        self._init()
        handlers = list(getGlobalSiteManager().registeredHandlers())
        self.assertIn(on_pub_failure, [h.handler for h in handlers])

    def test_request_gets_isolated_scope_and_transaction(self):
        self._init()
        outer = sentry_sdk.get_isolation_scope()
        environ = {"PATH_INFO": "/plone/some-view", "REQUEST_METHOD": "GET"}
        body = WSGIPublisher.publish_module(environ, lambda *a: None)
        self.assertEqual(body, [b"ok"])
        inner = self.calls[0]
        self.assertIsNot(inner, outer)
        self.assertEqual(inner._transaction, "/plone/some-view")
