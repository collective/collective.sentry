from collective.sentry.tests.plone_layer import SENTRY_FUNCTIONAL_TESTING
from collective.sentry.tests.utils import captured_events
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.testing.zope import Browser

import sentry_sdk
import transaction
import unittest


class FunctionalBase(unittest.TestCase):
    layer = SENTRY_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.transport = self.layer["sentry_transport"]
        self.transport.envelopes.clear()
        transaction.commit()

    def _browser(self, auth=True):
        # The standard testbrowser calls the ``publish_module`` it imported
        # at module load, like ``Zope2.Startup.run.make_wsgi_app`` does for
        # a real WSGI server, so it never sees a later patch of that name.
        browser = Browser(self.layer["app"])
        browser.handleErrors = True
        browser.raiseHttpErrors = False
        if auth:
            browser.addHeader(
                "Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}"
            )
        return browser

    def _events(self):
        sentry_sdk.get_client().flush()
        return captured_events(self.transport)


class TestBasicCapture(FunctionalBase):
    def test_exception_produces_one_enriched_event(self):
        browser = self._browser()
        browser.open(self.portal.absolute_url() + "/@@sentry-test-boom?q=fish")
        events = self._events()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["exception"]["values"][-1]["value"], "sentry-test boom")
        self.assertEqual(event["extra"]["form"]["q"], "'fish'")
        for key in ("cookies", "lazy items", "other", "request"):
            self.assertIn(key, event["extra"])
        self.assertEqual(event["user"]["id"], SITE_OWNER_NAME)
        self.assertIn("sentry-test-boom", event["transaction"])


class TestIgnoredExceptions(FunctionalBase):
    def test_error_log_ignored_exception_sends_nothing(self):
        error_log = self.portal.error_log
        # NotFound is in Plone's default ignored list; assert instead of
        # assuming, so the test fails loudly if defaults change.
        self.assertIn("NotFound", error_log._ignored_exceptions)
        transaction.commit()
        browser = self._browser()
        browser.open(self.portal.absolute_url() + "/@@sentry-test-notfound")
        self.assertEqual(self._events(), [])


class TestIgnoredExceptionsBelowViews(FunctionalBase):
    """The portal's ignored list also applies when PARENTS[0] cannot acquire
    error_log, like a view in front of an image scale or download (#48)."""

    def setUp(self):
        super().setUp()
        error_log = self.portal.error_log
        props = error_log.getProperties()
        self._orig_ignored = props["ignored_exceptions"]
        error_log.setProperties(
            props["keep_entries"],
            props["copy_to_zlog"],
            self._orig_ignored + ("SentryTestIgnored",),
        )
        # Only the portal ignores it, so a lookup that ends at the Zope root
        # is caught as well.
        root_error_log = getattr(self.layer["app"], "error_log", None)
        self.assertNotIn(
            "SentryTestIgnored", getattr(root_error_log, "_ignored_exceptions", ())
        )
        transaction.commit()

    def tearDown(self):
        error_log = self.portal.error_log
        props = error_log.getProperties()
        error_log.setProperties(
            props["keep_entries"], props["copy_to_zlog"], self._orig_ignored
        )
        transaction.commit()

    def _open(self, path):
        self._browser().open(self.portal.absolute_url() + path)
        return self._events()

    def test_ignored_on_view_of_portal(self):
        self.assertEqual(self._open("/@@sentry-test-traverse"), [])

    def test_ignored_on_object_below_view(self):
        self.assertEqual(self._open("/@@sentry-test-traverse/sub"), [])

    def test_ignored_during_traversal(self):
        self.assertEqual(self._open("/@@sentry-test-traverse/fail"), [])

    def test_not_ignored_is_still_captured(self):
        events = self._open("/@@sentry-test-boom")
        self.assertEqual(len(events), 1)


class TestLoggingPath(FunctionalBase):
    def test_log_error_event_is_request_enriched(self):
        browser = self._browser()
        browser.open(self.portal.absolute_url() + "/@@sentry-test-log?marker=abc")
        events = self._events()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["logentry"]["message"], "sentry-test log")
        self.assertIn("sentry-test-log", event["extra"]["request"]["url"])
        self.assertEqual(event["extra"]["form"]["marker"], "'abc'")


class TestScopeIsolation(FunctionalBase):
    def test_no_scope_bleed_between_requests(self):
        browser = self._browser()
        browser.open(self.portal.absolute_url() + "/@@sentry-test-boom?first=1")
        browser.open(self.portal.absolute_url() + "/@@sentry-test-boom")
        events = self._events()
        self.assertEqual(len(events), 2)
        self.assertIn("first", events[0]["extra"]["form"])
        self.assertNotIn("first", events[1]["extra"]["form"])
