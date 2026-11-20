"""Views for the functional tests. Only imported by the Plone test layer."""

from Products.Five.browser import BrowserView
from zExceptions import NotFound
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse

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


class SentryTestIgnored(Exception):
    """Ignored only in the portal's error_log, not in the Zope root's."""


class _SubObject:
    """Published below a view, like an image scale below ``@@images``.

    Not acquisition-wrapped: it only knows its view via ``__parent__``.
    """

    def __init__(self, parent):
        self.__parent__ = parent

    def __call__(self):
        raise SentryTestIgnored("sentry-test ignored")


@implementer(IPublishTraverse)
class TraverseView(BrowserView):
    """``@@sentry-test-traverse/sub`` publishes a sub-object of this view;
    ``@@sentry-test-traverse/fail`` raises while traversing."""

    def publishTraverse(self, request, name):
        if name == "fail":
            raise SentryTestIgnored("sentry-test ignored during traversal")
        return _SubObject(self)

    def __call__(self):
        raise SentryTestIgnored("sentry-test ignored")
