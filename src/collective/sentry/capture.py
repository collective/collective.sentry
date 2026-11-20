"""Exception capture for the Zope publisher. Zope-only — no Plone imports."""

from zope.component import adapter
from zope.component.hooks import getSite
from ZPublisher.interfaces import IPubFailure

import sentry_sdk


def _find_error_log(request):
    """The error_log whose settings apply to this request.

    First the error_log of the site the request traversed into (the Plone
    portal). request.PARENTS[0] alone is not enough there: below a view,
    such as an image scale below @@images, it is that view, which cannot
    acquire error_log; and when traversal fails, PARENTS is still in
    traversal order, so PARENTS[0] is the Zope root.

    Without a site (plain Zope), acquire it from request.PARENTS[0], which
    finds the root Products.SiteErrorLog instance.
    """
    error_log = getattr(getSite(), "error_log", None)
    if error_log is not None:
        return error_log
    parents = getattr(request, "PARENTS", None) or []
    context = parents[0] if parents else None
    return getattr(context, "error_log", None) if context is not None else None


def should_ignore(exc_type, request):
    """True if the site's error_log lists this exception type as ignored."""
    if exc_type is None:
        return False
    ignored = getattr(_find_error_log(request), "_ignored_exceptions", ())
    return exc_type.__name__ in ignored


@adapter(IPubFailure)
def on_pub_failure(event):
    """IPubFailure handler; registered by ZopeIntegration.setup_once().

    BBB: the @adapter decorator lets ZCML register this with a bare
    <subscriber handler="..."/> (no for=), matching 1.x's
    errorRaisedSubscriber.
    """
    if getattr(event, "retry", False):
        # Zope republishes (e.g. ConflictError retries); only the final
        # failure is worth reporting.
        return
    exc_info = event.exc_info
    if should_ignore(exc_info[0], event.request):
        return
    sentry_sdk.capture_exception(exc_info)
