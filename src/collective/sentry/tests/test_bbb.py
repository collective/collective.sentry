import importlib
import sys
import unittest
import warnings


class TestBBBShim(unittest.TestCase):
    def test_import_warns_and_reexports(self):
        sys.modules.pop("collective.sentry.error_handler", None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            module = importlib.import_module("collective.sentry.error_handler")
        self.assertTrue(any(w.category is DeprecationWarning for w in caught))
        from collective.sentry.capture import on_pub_failure
        from collective.sentry.extraction import request_event_processor

        self.assertIs(module.errorRaisedSubscriber, on_pub_failure)
        event = {"extra": {"pre": "set"}}
        self.assertEqual(module.before_send(event, {}), event)
        self.assertIs(module.before_send.__wrapped__, request_event_processor)
