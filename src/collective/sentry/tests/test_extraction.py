from collective.sentry.tests.utils import FakeRequest

import unittest


class BrokenRepr:
    def __repr__(self):
        raise ValueError("no repr for you")


class TestSections(unittest.TestCase):
    def test_form_filters_passwords(self):
        from collective.sentry.extraction import _get_form

        req = FakeRequest(form={"name": "jens", "password": "geheim"})
        form = _get_form(req)
        self.assertEqual(form["name"], "'jens'")
        self.assertNotIn("geheim", str(form))

    def test_request_info_extracts_http_headers_only(self):
        from collective.sentry.extraction import _get_request_info

        req = FakeRequest(
            environ={
                "REMOTE_ADDR": "10.0.0.1",
                "QUERY_STRING": "a=b",
                "HTTP_USER_AGENT": "UA",
                "CONTENT_TYPE": "text/html",
                "wsgi.input": object(),
                "SERVER_SOFTWARE": "waitress",
            }
        )
        info = _get_request_info(req)
        self.assertEqual(info["headers"]["User-Agent"], "UA")
        self.assertEqual(info["headers"]["Content-Type"], "text/html")
        self.assertNotIn("wsgi.input", info["headers"])
        self.assertNotIn("SERVER_SOFTWARE", info["headers"])
        self.assertEqual(info["url"], "http://nohost/plone/view")
        self.assertEqual(info["method"], "GET")
        self.assertEqual(info["host"], "10.0.0.1")
        self.assertEqual(info["query_string"], "a=b")

    def test_request_info_filters_sensitive_headers(self):
        from collective.sentry.extraction import _get_request_info

        req = FakeRequest(
            environ={
                "REMOTE_ADDR": "10.0.0.1",
                "HTTP_AUTHORIZATION": "Basic dXNlcjpwYXNz",
                "HTTP_COOKIE": "__ac=secret",
                "HTTP_USER_AGENT": "UA",
            }
        )
        info = _get_request_info(req)
        # No active client -> should_send_default_pii() is False by default.
        self.assertEqual(info["headers"]["Authorization"], "[Filtered]")
        self.assertEqual(info["headers"]["Cookie"], "[Filtered]")
        self.assertEqual(info["headers"]["User-Agent"], "UA")

    def test_safe_isolates_section_failure(self):
        from collective.sentry.extraction import _get_form
        from collective.sentry.extraction import _safe

        req = FakeRequest(form={"bad": BrokenRepr()})
        result = _safe(_get_form, req)
        self.assertEqual(result, {"error": "extraction failed: ValueError"})

    def test_user_without_getproperty(self):
        from collective.sentry.extraction import _get_user

        class PlainZopeUser:
            def getId(self):
                return "zopeadmin"

        req = FakeRequest(other={"AUTHENTICATED_USER": PlainZopeUser()})
        self.assertEqual(_get_user(req), {"id": "zopeadmin"})

    def test_user_with_getproperty(self):
        from collective.sentry.extraction import _get_user

        class PASUser:
            def getId(self):
                return "jens"

            def getProperty(self, name, default=None):
                return "jens@example.org"

        req = FakeRequest(other={"AUTHENTICATED_USER": PASUser()})
        self.assertEqual(_get_user(req), {"id": "jens", "email": "jens@example.org"})


class TestProcessor(unittest.TestCase):
    def _run(self, request):
        from collective.sentry.extraction import request_event_processor

        import zope.globalrequest

        zope.globalrequest.setRequest(request)
        try:
            return request_event_processor({"extra": {}}, {})
        finally:
            zope.globalrequest.clearRequest()

    def test_enriches_event(self):
        event = self._run(FakeRequest(form={"q": "fish"}))
        self.assertEqual(event["extra"]["form"]["q"], "'fish'")
        for key in ("cookies", "lazy items", "other", "request"):
            self.assertIn(key, event["extra"])

    def test_no_request_returns_event_unchanged(self):
        from collective.sentry.extraction import request_event_processor

        event = {"extra": {}}
        self.assertIs(request_event_processor(event, {}), event)

    def test_never_drops_event_on_failure(self):
        event = self._run(FakeRequest(form={"bad": BrokenRepr()}))
        self.assertIsNotNone(event)
        self.assertIn("error", event["extra"]["form"])

    def test_respects_existing_keys(self):
        from collective.sentry.extraction import request_event_processor

        import zope.globalrequest

        zope.globalrequest.setRequest(FakeRequest(form={"q": "fish"}))
        try:
            event = {"extra": {"form": {"pre": "set"}}}
            out = request_event_processor(event, {})
            self.assertEqual(out["extra"]["form"], {"pre": "set"})
        finally:
            zope.globalrequest.clearRequest()

    def test_authenticated_user_in_processor(self):
        class PASUser:
            def getId(self):
                return "jens"

            def getProperty(self, name, default=None):
                return "jens@example.org"

        event = self._run(FakeRequest(other={"AUTHENTICATED_USER": PASUser()}))
        self.assertEqual(
            event["extra"]["user"], {"id": "jens", "email": "jens@example.org"}
        )
        self.assertEqual(event["user"], {"id": "jens", "email": "jens@example.org"})

    def test_get_user_failure_in_processor(self):
        class BrokenUser:
            def getId(self):
                raise RuntimeError("getId broken")

        event = self._run(FakeRequest(other={"AUTHENTICATED_USER": BrokenUser()}))
        self.assertEqual(
            event["extra"]["user"], {"error": "extraction failed: RuntimeError"}
        )
        self.assertNotIn("user", event)
