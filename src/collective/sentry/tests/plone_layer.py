"""plone.app.testing layer with a capturing Sentry client."""

from collective.sentry.integration import ZopeIntegration
from collective.sentry.tests.utils import CapturingTransport
from collective.sentry.tests.utils import reset_sentry
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from zope.testbrowser import browser as _zope_testbrowser
from zope.testbrowser.browser import Browser as WSGIBrowser
from ZPublisher import WSGIPublisher
from ZPublisher.httpexceptions import HTTPExceptionHandler
from ZPublisher.utils import basic_auth_encode

import re
import sentry_sdk

# --- late-binding functional-testing Browser -------------------------------
#
# ``plone.testing.zope.Browser`` (really ``plone.testing._z2_testbrowser
# .Browser``) drives its requests through
# ``from ZPublisher.WSGIPublisher import publish_module`` -- a name bound
# once, at module-import time, to whatever function object
# ``ZPublisher.WSGIPublisher.publish_module`` pointed at back then. That
# import happens as a side effect of importing ``plone.testing.zope``
# (typically at test-discovery time), which is *before*
# ``SentryLayer.setUpZope`` runs ``sentry_sdk.init()`` and, with it,
# ``ZopeIntegration.setup_once()`` -- the code that replaces the
# *attribute* ``ZPublisher.WSGIPublisher.publish_module`` with a
# Sentry-wrapped version. Because the testbrowser's own module captured
# the original function by value, it keeps calling the unwrapped
# publisher forever, no matter when ``publish_module`` is reassigned.
#
# Symptom observed here: not "0 events" but a *single, unenriched* event --
# ``on_pub_failure`` still fires because it is registered globally as an
# ``IPubFailure`` subscriber (independent of the publish_module wrap), but
# ``sentry_sdk.capture_exception`` runs outside the ``isolation_scope`` our
# wrapper would have opened, so ``request_event_processor`` was never
# attached and the transaction name was never set.
#
# The fix: re-look up ``WSGIPublisher.publish_module`` *at call time*
# (attribute access, not a frozen import), so we always dispatch through
# whatever function is currently installed there -- the Sentry-wrapped one,
# once ``setup_once()`` has run. Everything else below mirrors
# ``plone.testing._z2_testbrowser`` byte for byte.

_BASIC_RE = re.compile("Basic (.+)?:(.+)?$")


def _auth_header(header):
    match = _BASIC_RE.match(header)
    if match:
        user, password = match.group(1, 2)
        return basic_auth_encode(user or "", password or "")
    return header


def _save_state(func):
    """Save/restore threadlocal security manager and local site around a
    call, exactly as ``plone.testing._z2_testbrowser.saveState`` does.
    """
    from AccessControl.SecurityManagement import getSecurityManager
    from AccessControl.SecurityManagement import setSecurityManager
    from zope.component.hooks import getSite
    from zope.component.hooks import setSite

    def wrapped(*args, **kw):
        sm, site = getSecurityManager(), getSite()
        try:
            return func(*args, **kw)
        finally:
            setSecurityManager(sm)
            setSite(site)

    return wrapped


class _LateBindingCaller:
    """Like ``plone.testing._z2_testbrowser.Zope2Caller``, but reads
    ``WSGIPublisher.publish_module`` at call time instead of freezing it.
    """

    def __init__(self, browser, app):
        self.browser = browser
        self.app = app

    @_save_state
    def __call__(self, environ, start_response):
        http_auth = "HTTP_AUTHORIZATION"
        if http_auth in environ:
            environ[http_auth] = _auth_header(environ[http_auth])

        publish = WSGIPublisher.publish_module
        if self.browser.handleErrors:
            publish = HTTPExceptionHandler(publish)
        wsgi_result = publish(environ, start_response)

        self.app._p_jar.sync()
        return wsgi_result


class LateBindingBrowser(WSGIBrowser):
    """Drop-in replacement for ``plone.testing.zope.Browser`` that always
    dispatches through the *current* ``WSGIPublisher.publish_module``, so it
    sees the Sentry wrap installed by ``ZopeIntegration.setup_once()``.
    """

    handleErrors = True
    raiseHttpErrors = True

    def __init__(self, app, url=None):
        super().__init__(url=url, wsgi_app=_LateBindingCaller(self, app))


# Allow the ``http://nohost/...`` URLs plone.app.testing sites use, exactly
# as ``plone.testing._z2_testbrowser`` does for its own Browser.
_zope_testbrowser._allowed.add("nohost")


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
            integrations=[ZopeIntegration()],
        )

    def tearDownZope(self, app):
        reset_sentry()


SENTRY_FIXTURE = SentryLayer()
SENTRY_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(SENTRY_FIXTURE,), name="CollectiveSentry:Functional"
)
