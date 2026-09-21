from collective.sentry.tests.plone_layer import LateBindingBrowser
from collective.sentry.tests.plone_layer import SENTRY_FUNCTIONAL_TESTING
from collective.sentry.tests.utils import captured_events
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

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
        browser = LateBindingBrowser(self.layer["app"])
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
