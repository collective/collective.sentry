"""plone.app.testing layer with a capturing Sentry client."""

from collective.sentry.integration import ZopeIntegration
from collective.sentry.tests.utils import CapturingTransport
from collective.sentry.tests.utils import reset_sentry
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from sentry_sdk.integrations.logging import LoggingIntegration

import logging
import sentry_sdk


class SentryLayer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import collective.sentry.tests

        self.loadZCML(package=collective.sentry.tests, name="testing.zcml")
        reset_sentry()
        self["sentry_transport"] = CapturingTransport()
        sentry_sdk.init(
            dsn="https://x@example.com/1",
            transport=self["sentry_transport"],
            integrations=[
                ZopeIntegration(),
                LoggingIntegration(
                    breadcrumb_level=logging.INFO,
                    level=None,
                    event_level=logging.ERROR,
                ),
            ],
        )

    def tearDownZope(self, app):
        reset_sentry()


SENTRY_FIXTURE = SentryLayer()
SENTRY_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(SENTRY_FIXTURE,), name="CollectiveSentry:Functional"
)
