"""Exception capture for the Zope publisher. Zope-only — no Plone imports."""

from zope.component import adapter
from ZPublisher.interfaces import IPubFailure

import sentry_sdk


def should_ignore(exc_type, request):
    """True if the site's error_log lists this exception type as ignored.

    Resolves the nearest error_log by acquisition from request.PARENTS[0]:
    inside a Plone site that is the portal's tool, on plain Zope the root
    Products.SiteErrorLog instance.
    """
    if exc_type is None:
        return False
    parents = getattr(request, "PARENTS", None) or []
    context = parents[0] if parents else None
    error_log = getattr(context, "error_log", None) if context is not None else None
    ignored = getattr(error_log, "_ignored_exceptions", ())
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
