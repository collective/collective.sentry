#! -*- coding : utf-8 -*-

# Integration of Zope (4) with Sentry
# The code below is heavily based on the raven.contrib. zope module

import os
import logging
import sentry_sdk
import sentry_sdk.utils as sentry_utils

from App.config import getConfiguration
from zope.component import adapter
from zope.globalrequest import getRequest
from AccessControl.users import nobody
from ZPublisher.interfaces import IPubFailure
from ZPublisher.HTTPRequest import _filterPasswordFields

sentry_dsn = os.environ.get("SENTRY_DSN")

sentry_project = os.environ.get("SENTRY_PROJECT")

is_sentry_optional = os.environ.get("SENTRY_OPTIONAL")

sentry_max_length = os.environ.get("SENTRY_MAX_LENGTH")

cookies_filter_blacklist = os.environ.get("COOKIES_FILTER_BLACKLIST")


def _before_send(event, hint):
    """
     Inject Plone/Zope specific information (based on raven.contrib.zope)
    """

    request = getRequest()
    if not request:
        return event

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

    event["extra"]["request"] = http

    event["extra"]["form"] = {}
    event["extra"]["other"] = {}
    event["extra"]["cookies"] = {}
    event["extra"]["lazy items"] = {}

    for k, v in _filterPasswordFields(request.form.items()):
        event["extra"]["form"][k] = repr(v)

    for k, v in _filter_cookies_fields(request.cookies.items()):
        event["extra"]["cookies"][k] = repr(v)

    for k, v in _filterPasswordFields(request._lazies.items()):
        event["extra"]["lazy items"][k] = repr(v)

    for k, v in _filterPasswordFields(request.other.items()):
        if k in ('PARENTS', 'RESPONSE'):
            continue
        event["extra"]["other"][k] = repr(v)

    user = request.get("AUTHENTICATED_USER", None)
    if user is not None and user != nobody:
        user_dict = {
            "id": user.getId(),
            "email": user.getProperty("email") or "",
        }
    else:
        user_dict = {}
    event["extra"]["user"] = user_dict

    return event


def _filter_cookies_fields(request_cookies_items):
    if(not cookies_filter_blacklist):
        return _filterPasswordFields(request_cookies_items)
    else:
        blacklist = cookies_filter_blacklist.split(';')
        filtered_dict = dict()
        for k, v in _filterPasswordFields(request_cookies_items):
            if k not in blacklist:
                filtered_dict[k] = v
        return filtered_dict.items()


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
        debug=False
    )

    configuration = getConfiguration()
    tags = {}
    instancehome = configuration.instancehome
    tags['instance_name'] = instancehome.rsplit(os.path.sep, 1)[-1]

    with sentry_sdk.configure_scope() as scope:
        for k, v in tags.items():
            scope.set_tag(k, v)
        if sentry_project:
            scope.set_tag("project", sentry_project)

    logging.info("Sentry integration enabled")


# fake registration in order to import the file properly
# for the sentry_skd.init() call
@adapter(IPubFailure)
def dummy(event):
    pass
