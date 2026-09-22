"""Shared test helpers. Zope-only — no Plone imports."""

from io import BytesIO

import logging
import sentry_sdk

# LoggingIntegration.setup_once() unconditionally rebinds
# logging.Logger.callHandlers to a closure wrapping whatever was there
# before -- captured here, at first import, before any test has called
# sentry_sdk.init(). Needed by reset_sentry() below.
_ORIGINAL_CALL_HANDLERS = logging.Logger.callHandlers


class FakeRequest:
    """Duck-types the ZPublisher request surface extraction.py touches."""

    def __init__(
        self,
        form=None,
        cookies=None,
        other=None,
        lazies=None,
        environ=None,
        method="GET",
        url="http://nohost/plone/view",
    ):
        self.form = form or {}
        self.cookies = cookies or {}
        self.other = other or {}
        self._lazies = lazies or {}
        self.environ = environ or {
            "REMOTE_ADDR": "127.0.0.1",
            "QUERY_STRING": "x=1",
            "HTTP_USER_AGENT": "test-agent",
        }
        self.method = method
        self._url = url
        self.stdin = BytesIO(b"")

    def getURL(self):
        return self._url

    def get(self, key, default=None):
        return self.other.get(key, default)


class CapturingTransport(sentry_sdk.transport.Transport):
    """Collects envelopes instead of sending them."""

    def __init__(self, options=None):
        super().__init__(options)
        self.envelopes = []

    def capture_envelope(self, envelope):
        self.envelopes.append(envelope)


def captured_events(transport):
    return [e.get_event() for e in transport.envelopes if e.get_event()]


def reset_sentry():
    """Fresh SDK state per test: no active client, integrations re-runnable."""
    from sentry_sdk.integrations import _installed_integrations
    from sentry_sdk.integrations import _processed_integrations
    from sentry_sdk.scope import global_event_processors

    sentry_sdk.get_global_scope().clear()
    _installed_integrations.clear()
    _processed_integrations.clear()
    # Clearing _processed_integrations makes setup_once() re-run on the next
    # init(). For integrations that register through
    # add_global_event_processor (e.g. DedupeIntegration, ArgvIntegration,
    # ModulesIntegration, StdlibIntegration) that list is process-global and
    # append-only, so without clearing it here every test that re-inits
    # piles on another copy of each processor. Harmless alone, but
    # DedupeIntegration's processor marks an exception "seen" on its first
    # pass and drops it as a duplicate on its second -- so two or more
    # accumulated copies silently swallow every subsequent captured
    # exception across the whole process.
    global_event_processors.clear()
    # LoggingIntegration.setup_once() has the same append-only problem, but
    # worse: it rebinds the *class attribute*
    # logging.Logger.callHandlers to a closure over whatever
    # callHandlers was previously bound to, and never unwraps it. Since we
    # force setup_once() to re-run on every test by clearing
    # _processed_integrations above, each test that inits with
    # default_integrations enabled (the default) stacks another closure on
    # top of the last. Every stacked closure independently re-emits the
    # log record as an event, so one logger.error() call after N such
    # re-inits produces N duplicate Sentry events. Restore the pristine,
    # unwrapped callHandlers here so each test starts clean.
    logging.Logger.callHandlers = _ORIGINAL_CALL_HANDLERS
    # set_client(None) installs a NonRecordingClient -> is_active() False,
    # which the bootstrap's deployer-wins check relies on.
    sentry_sdk.get_global_scope().set_client(None)
