"""BBB shim. This module is deprecated since 2.0.

Enrichment lives in collective.sentry.extraction, capture in
collective.sentry.capture, initialization in collective.sentry.bootstrap.
"""

from collective.sentry.capture import on_pub_failure
from collective.sentry.extraction import request_event_processor

import functools
import warnings

errorRaisedSubscriber = on_pub_failure  # BBB: 1.x name for capture.on_pub_failure

warnings.warn(
    "collective.sentry.error_handler is deprecated; use "
    "collective.sentry.integration.ZopeIntegration instead.",
    DeprecationWarning,
    stacklevel=2,
)


@functools.wraps(request_event_processor)
def before_send(event, hint):
    """BBB: 1.x before_send; enrichment now runs as a scope processor."""
    return request_event_processor(event, hint)
