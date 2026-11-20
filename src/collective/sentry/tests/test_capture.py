from collective.sentry.tests.utils import captured_events
from collective.sentry.tests.utils import CapturingTransport
from collective.sentry.tests.utils import FakeRequest
from collective.sentry.tests.utils import reset_sentry
from unittest import mock

import sentry_sdk
import unittest


class FakeErrorLog:
    _ignored_exceptions = ("NotFound", "Unauthorized")


class FakeContext:
    error_log = FakeErrorLog()


def _request(with_error_log=True):
    req = FakeRequest()
    req.PARENTS = [FakeContext()] if with_error_log else []
    return req


class FakePubFailure:
    def __init__(self, exc, request, retry=False):
        try:
            raise exc
        except Exception:
            import sys

            self.exc_info = sys.exc_info()
        self.request = request
        self.retry = retry


class TestShouldIgnore(unittest.TestCase):
    def test_ignored_name_matches(self):
        from collective.sentry.capture import should_ignore

        class NotFound(Exception):
            pass

        self.assertTrue(should_ignore(NotFound, _request()))

    def test_unlisted_exception_not_ignored(self):
        from collective.sentry.capture import should_ignore

        self.assertFalse(should_ignore(RuntimeError, _request()))

    def test_no_error_log_found(self):
        from collective.sentry.capture import should_ignore

        self.assertFalse(should_ignore(RuntimeError, _request(False)))
        self.assertFalse(should_ignore(RuntimeError, object()))

    def test_none_exc_type(self):
        from collective.sentry.capture import should_ignore

        self.assertFalse(should_ignore(None, _request()))


class SiteErrorLog:
    _ignored_exceptions = ("Intercepted",)


class FakeSite:
    error_log = SiteErrorLog()


class TestShouldIgnoreWithSite(unittest.TestCase):
    """A site's error_log is used even when PARENTS[0] cannot acquire one."""

    def _should_ignore(self, exc_type, request, site):
        from collective.sentry.capture import should_ignore

        with mock.patch("collective.sentry.capture.getSite", return_value=site):
            return should_ignore(exc_type, request)

    def test_site_error_log_used_without_parents(self):
        class Intercepted(Exception):
            pass

        self.assertTrue(self._should_ignore(Intercepted, _request(False), FakeSite()))

    def test_site_error_log_wins_over_parents(self):
        class Intercepted(Exception):
            pass

        class NotFound(Exception):
            pass

        self.assertTrue(self._should_ignore(Intercepted, _request(), FakeSite()))
        self.assertFalse(self._should_ignore(NotFound, _request(), FakeSite()))

    def test_site_without_error_log_falls_back_to_parents(self):
        class NotFound(Exception):
            pass

        self.assertTrue(self._should_ignore(NotFound, _request(), object()))


class TestOnPubFailure(unittest.TestCase):
    def setUp(self):
        reset_sentry()
        self.transport = CapturingTransport()
        sentry_sdk.init(
            dsn="https://x@example.com/1",
            transport=self.transport,
            default_integrations=False,
        )

    def tearDown(self):
        reset_sentry()

    def test_captures_exception(self):
        from collective.sentry.capture import on_pub_failure

        on_pub_failure(FakePubFailure(RuntimeError("boom"), _request()))
        sentry_sdk.get_client().flush()
        events = captured_events(self.transport)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["exception"]["values"][0]["value"], "boom")

    def test_skips_retry(self):
        from collective.sentry.capture import on_pub_failure

        on_pub_failure(FakePubFailure(RuntimeError("boom"), _request(), retry=True))
        sentry_sdk.get_client().flush()
        self.assertEqual(captured_events(self.transport), [])

    def test_skips_ignored(self):
        from collective.sentry.capture import on_pub_failure

        class NotFound(Exception):
            pass

        on_pub_failure(FakePubFailure(NotFound("gone"), _request()))
        sentry_sdk.get_client().flush()
        self.assertEqual(captured_events(self.transport), [])
