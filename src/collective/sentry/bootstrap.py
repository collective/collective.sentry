"""Zero-config initialization from environment variables. Zope-only."""

from App.config import getConfiguration
from collective.sentry.integration import ZopeIntegration

import importlib
import logging
import os
import sentry_sdk
import warnings

logger = logging.getLogger(__name__)


def _load_integration(dotted):
    module_path, _, name = dotted.rpartition(".")
    try:
        module = importlib.import_module(module_path)
        return getattr(module, name)
    except (ImportError, AttributeError, ValueError) as exc:
        raise RuntimeError(
            f"SENTRY_INTEGRATIONS entry {dotted!r} cannot be loaded: {exc}"
        ) from exc


def initialize_from_environ(environ=None):
    """Init the SDK from env vars. Returns False when skipped."""
    environ = os.environ if environ is None else environ

    if "SENTRY_OPTIONAL" in environ:
        warnings.warn(
            "SENTRY_OPTIONAL is deprecated and ignored: a missing "
            "SENTRY_DSN never raises anymore.",
            DeprecationWarning,
            stacklevel=2,
        )

    if environ.get("SENTRY_DISABLE"):
        logger.info("Sentry disabled via SENTRY_DISABLE")
        return False
    if sentry_sdk.get_client().is_active():
        logger.info("Sentry already initialized, bootstrap skipped")
        return False
    dsn = environ.get("SENTRY_DSN")
    if not dsn:
        logger.info("SENTRY_DSN not set, Sentry reporting disabled")
        return False

    integrations = [ZopeIntegration()]
    raw = environ.get("SENTRY_INTEGRATIONS", "")
    for dotted in filter(None, (part.strip() for part in raw.split(","))):
        integrations.append(_load_integration(dotted)())

    extra_options = {}
    if "SENTRY_MAX_LENGTH" in environ:
        raw_max_length = environ["SENTRY_MAX_LENGTH"]
        try:
            extra_options["max_value_length"] = int(raw_max_length)
        except ValueError as exc:
            raise RuntimeError(
                "Environment variable SENTRY_MAX_LENGTH is malformed "
                f"(expected an integer): {raw_max_length}"
            ) from exc

    sentry_sdk.init(
        dsn=dsn,
        environment=environ.get("SENTRY_ENVIRONMENT"),
        integrations=integrations,
        attach_stacktrace=True,
        max_breadcrumbs=50,
        **extra_options,
    )

    scope = sentry_sdk.get_global_scope()
    instancehome = getattr(getConfiguration(), "instancehome", "") or ""
    if instancehome:
        scope.set_tag("instance_name", instancehome.rsplit(os.path.sep, 1)[-1])
    if environ.get("SENTRY_PROJECT"):
        scope.set_tag("project", environ["SENTRY_PROJECT"])

    logger.info("Sentry integration enabled")
    return True
