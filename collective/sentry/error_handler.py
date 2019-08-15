#! -*- coding : utf-8 -*-

# Integration of Zope (4) with Sentry
# The code below is heavily based on the raven.contrib. zope module

import os
import logging
import sentry_sdk
from inspect import getouterframes, currentframe, getinnerframes

from zope.component import adapter
from AccessControl.users import nobody
from ZPublisher.interfaces import IPubFailure
from ZPublisher.HTTPRequest import _filterPasswordFields


sentry_dsn = os.environ.get("SENTRY_DSN")
if not sentry_dsn:
    raise RuntimeError("Environment variable SENTRY_DSN not configured")


def before_send(event, hint):

    request = None
    exc_info = None
    for frame_info in getouterframes(currentframe()):
        frame = frame_info[0]
        if not request:
            request = frame.f_locals.get("request", None)
            if not request:
                view = frame.f_locals.get("self", None)
                try:
                    request = getattr(view, "request", None)
                except RuntimeError:
                    request = None
        if not exc_info:
            exc_info = frame.f_locals.get("exc_info", None)
            if not hasattr(exc_info, "__getitem__"):
                exc_info = None
        if request and exc_info:
            break

    if request:

        # ensure that all header key-value pairs are strings
        headers = dict()
        for k, v in request.environ.items():
            if not isinstance(v, str):
                v = str(v)
            headers[k] = v

        try:
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

            for k, v in _filterPasswordFields(request.items()):
                event["extra"]["form"][k] = repr(v)

            for k, v in _filterPasswordFields(request.cookies.items()):
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

        except (AttributeError, KeyError):
            logging.warn("Could not extract data from request", exc_info=True)

    return event

sentry_sdk.init(sentry_dsn, max_breadcrumbs=50, before_send=before_send, debug=False)


# fake registration in order to import the file properly for the sentry_skd.init() call
@adapter(IPubFailure)
def dummy(event):
    pass
