#! -*- coding : utf-8 -*-

# Integration of Zope (4) with Sentry
# The code below is heavily based on the raven.contrib. zope module

import logging
import os
import sys
import traceback

import sentry_sdk
import sentry_sdk.utils as sentry_utils
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.users import nobody
from App.config import getConfiguration
from plone import api
from plone.api.exc import CannotGetPortalError
from sentry_sdk.integrations.logging import ignore_logger
from zope.component import adapter
from zope.globalrequest import getRequest
from ZPublisher.HTTPRequest import _filterPasswordFields
from ZPublisher.interfaces import IPubFailure

sentry_dsn = os.environ.get("SENTRY_DSN")

sentry_project = os.environ.get("SENTRY_PROJECT")

sentry_environment = os.environ.get("SENTRY_ENVIRONMENT")

is_sentry_optional = os.environ.get("SENTRY_OPTIONAL")

sentry_max_length = os.environ.get("SENTRY_MAX_LENGTH")


def _get_user_from_request(request):
    user = request.get("AUTHENTICATED_USER", None)

    if user is None:
        user = getSecurityManager().getUser()

    if user is not None and user != nobody:
        user_dict = {
            "id": user.getId(),
            "email": user.getProperty("email") or "",
        }
    else:
        user_dict = {}

    return user_dict


def _get_other_from_request(request):
    other = {}
    for k, v in _filterPasswordFields(request.other.items()):
        if k in ("PARENTS", "RESPONSE"):
            continue
        other[k] = repr(v)
    return other


def _get_lazyitems_from_request(request):
    lazy_items = {}
    for k, v in _filterPasswordFields(request._lazies.items()):
        lazy_items[k] = repr(v)
    return lazy_items


def _get_cookies_from_request(request):
    cookies = {}
    for k, v in _filterPasswordFields(request.cookies.items()):
        cookies[k] = repr(v)
    return cookies


def _get_form_from_request(request):
    form = {}
    for k, v in _filterPasswordFields(request.form.items()):
        form[k] = repr(v)
    return form


def _get_request_from_request(request):
    # ensure that all header key-value pairs are strings
    headers = dict()
    for k, v in request.environ.items():
        if not isinstance(v, str):
            v = str(v)
        headers[k] = v

    body_pos = request.stdin.tell()
    request.stdin.seek(0)
    body = request.stdin.read()
    request.stdin.seek(body_pos)
    http = dict(
        headers=headers,
        url=request.getURL(),
        method=request.method,
        host=request.environ.get("REMOTE_ADDR", ""),
    )
    if "HTTP_USER_AGENT" in http["headers"]:
        if "User-Agent" not in http["headers"]:
            http["headers"]["User-Agent"] = http["headers"]["HTTP_USER_AGENT"]
    if "QUERY_STRING" in http["headers"]:
        http["query_string"] = http["headers"]["QUERY_STRING"]

    return http


def _before_send(event, hint):
    """
     Inject Plone/Zope specific information (based on raven.contrib.zope)
    """
    request = getRequest()

    if request:
        # We have no request if event is captured by errorRaisedSubscriber (see below)
        # so extra information must be set there.
        # If the event is send by pythons logging module we set extra info here.
        if not "other" in event["extra"]:
            event["extra"]["other"] = _get_other_from_request(request)
        if not "lazy items" in event["extra"]:
            event["extra"]["lazy items"] = _get_lazyitems_from_request(request)
        if not "cookies" in event["extra"]:
            event["extra"]["cookies"] = _get_cookies_from_request(request)
        if not "form" in event["extra"]:
            event["extra"]["form"] = _get_form_from_request(request)
        if not "request" in event["extra"]:
            event["extra"]["request"] = _get_request_from_request(request)
        user_info = _get_user_from_request(request)
        if not "user" in event["extra"]:
            event["extra"]["user"] = user_info
        if not "user" in event:
            event["user"] = user_info

    return event


def before_send(event, hint):
    try:
        return _before_send(event, hint)
    except KeyError:
        logging.warning("Could not extract data from request", exc_info=True)


if not sentry_dsn:
    msg = "Environment variable SENTRY_DSN not configured"
    if is_sentry_optional:
        logging.info(msg)
    else:
        raise RuntimeError(msg)

if sentry_dsn:
    if sentry_max_length:
        try:
            sentry_max_length = int(sentry_max_length)
        except ValueError:
            msg = "Environment variable SENTRY_MAX_LENGTH is malformed"
            raise RuntimeError(msg)
        else:
            sentry_utils.MAX_STRING_LENGTH = sentry_max_length

    sentry_sdk.init(
        sentry_dsn,
        max_breadcrumbs=50,
        before_send=before_send,
        attach_stacktrace=True,
        debug=False,
        environment=sentry_environment,
    )

    configuration = getConfiguration()
    tags = {}
    instancehome = configuration.instancehome
    tags["instance_name"] = instancehome.rsplit(os.path.sep, 1)[-1]

    with sentry_sdk.configure_scope() as scope:
        for k, v in tags.items():
            scope.set_tag(k, v)
        if sentry_project:
            scope.set_tag("project", sentry_project)

    logging.info("Sentry integration enabled")
    ignore_logger("Zope.SiteErrorLog")


@adapter(IPubFailure)
def errorRaisedSubscriber(event):
    exc_info = (
        sys.exc_info()
    )  # Save exc_info before new exceptions (CannotGetPortalError) arise
    try:
        error_log = api.portal.get_tool(name="error_log")
    except CannotGetPortalError:
        # Try to get Zope root.
        try:
            error_log = event.request.PARENTS[0].error_log
        except (AttributeError, KeyError, IndexError):
            error_log = None

    if error_log and exc_info[0].__name__ in error_log._ignored_exceptions:
        return

    with sentry_sdk.push_scope() as scope:
        scope.set_extra("other", _get_other_from_request(event.request))
        scope.set_extra("lazy items", _get_lazyitems_from_request(event.request))
        scope.set_extra("cookies", _get_cookies_from_request(event.request))
        scope.set_extra("form", _get_form_from_request(event.request))
        scope.set_extra("request", _get_request_from_request(event.request))
        user_info = _get_user_from_request(event.request)
        scope.set_extra("user", user_info)
        if user_info and "id" in user_info:
            scope.user = user_info

        sentry_sdk.capture_exception(exc_info)
