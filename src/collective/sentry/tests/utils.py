"""Shared test helpers. Zope-only — no Plone imports."""

from io import BytesIO

import sentry_sdk


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

    sentry_sdk.get_global_scope().clear()
    _installed_integrations.clear()
    _processed_integrations.clear()
    # set_client(None) installs a NonRecordingClient -> is_active() False,
    # which the bootstrap's deployer-wins check relies on.
    sentry_sdk.get_global_scope().set_client(None)
