from collective.sentry.tests.utils import CapturingTransport
from collective.sentry.tests.utils import reset_sentry
from zope.component import getGlobalSiteManager
from ZPublisher import WSGIPublisher
from ZPublisher.interfaces import IPubFailure

import sentry_sdk
import unittest
import warnings

DSN = "https://x@example.com/1"


class TestBootstrap(unittest.TestCase):
    def setUp(self):
        reset_sentry()
        self._orig_publish_module = WSGIPublisher.publish_module

    def tearDown(self):
        # initialize_from_environ() runs ZopeIntegration.setup_once(), which
        # wraps WSGIPublisher.publish_module and registers on_pub_failure as
        # an IPubFailure handler. Undo both, or a later test/layer that
        # checks the "_sentry_wrapped" guard thinks setup already happened
        # and skips it -- while the handler registration itself doesn't
        # survive a zope.testing.cleanup.cleanUp() (e.g. at the start of the
        # functional test layer), leaving no handler registered at all.
        WSGIPublisher.publish_module = self._orig_publish_module
        from collective.sentry.capture import on_pub_failure

        getGlobalSiteManager().unregisterHandler(on_pub_failure, (IPubFailure,))
        reset_sentry()

    def _call(self, **env):
        from collective.sentry.bootstrap import initialize_from_environ

        return initialize_from_environ(env)

    def test_disable_wins(self):
        self.assertFalse(self._call(SENTRY_DISABLE="1", SENTRY_DSN=DSN))

    def test_missing_dsn_skips_without_error(self):
        self.assertFalse(self._call())

    def test_optional_is_deprecated(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self._call(SENTRY_OPTIONAL="1")
        self.assertTrue(any(w.category is DeprecationWarning for w in caught))

    def test_deployer_init_wins(self):
        sentry_sdk.init(
            dsn=DSN, transport=CapturingTransport(), default_integrations=False
        )
        self.assertFalse(self._call(SENTRY_DSN=DSN))

    def test_initializes_with_zope_integration(self):
        from collective.sentry.integration import ZopeIntegration

        self.assertTrue(self._call(SENTRY_DSN=DSN, SENTRY_ENVIRONMENT="testing"))
        client = sentry_sdk.get_client()
        self.assertTrue(client.is_active())
        self.assertEqual(client.options["environment"], "testing")
        self.assertIsNotNone(client.get_integration(ZopeIntegration))

    def test_max_length_only_when_set(self):
        self._call(SENTRY_DSN=DSN)
        default_len = sentry_sdk.get_client().options["max_value_length"]
        reset_sentry()
        self._call(SENTRY_DSN=DSN, SENTRY_MAX_LENGTH="512")
        self.assertEqual(sentry_sdk.get_client().options["max_value_length"], 512)
        self.assertNotEqual(default_len, 512)

    def test_malformed_max_length_raises_clear_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            self._call(SENTRY_DSN=DSN, SENTRY_MAX_LENGTH="abc")
        self.assertIn("SENTRY_MAX_LENGTH", str(ctx.exception))

    def test_extra_integrations_loaded(self):
        self.assertTrue(
            self._call(
                SENTRY_DSN=DSN,
                SENTRY_INTEGRATIONS="sentry_sdk.integrations.argv.ArgvIntegration",
            )
        )
        from sentry_sdk.integrations.argv import ArgvIntegration

        self.assertIsNotNone(sentry_sdk.get_client().get_integration(ArgvIntegration))

    def test_bogus_integration_name_raises_clear_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            self._call(SENTRY_DSN=DSN, SENTRY_INTEGRATIONS="no.such.Thing")
        self.assertIn("SENTRY_INTEGRATIONS", str(ctx.exception))

    def test_dotless_integration_name_raises_clear_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            self._call(SENTRY_DSN=DSN, SENTRY_INTEGRATIONS="BadName")
        self.assertIn("SENTRY_INTEGRATIONS", str(ctx.exception))

    def test_project_tag_set(self):
        self._call(SENTRY_DSN=DSN, SENTRY_PROJECT="portal")
        # global scope tags land on every event
        self.assertEqual(sentry_sdk.get_global_scope()._tags.get("project"), "portal")
