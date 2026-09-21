"""Views for the functional tests. Only imported by the Plone test layer."""

from Products.Five.browser import BrowserView
from zExceptions import NotFound

import logging


class BoomView(BrowserView):
    def __call__(self):
        raise RuntimeError("sentry-test boom")


class NotFoundView(BrowserView):
    def __call__(self):
        raise NotFound("sentry-test gone")


class LogView(BrowserView):
    def __call__(self):
        logging.getLogger("collective.sentry.tests").error("sentry-test log")
        return "logged"
