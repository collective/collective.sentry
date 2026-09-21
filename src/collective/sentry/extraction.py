"""Request-data extraction for Sentry events. Zope-only — no Plone imports."""

from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.users import nobody
from sentry_sdk.scope import should_send_default_pii
from zope.globalrequest import getRequest
from ZPublisher.HTTPRequest import _filterPasswordFields

# Header names as produced by the key[5:].replace("_", "-").title()
# transform below; filtered out unless PII sending is explicitly enabled.
SENSITIVE_HEADERS = frozenset(
    {
        "Authorization",
        "Cookie",
        "Set-Cookie",
        "X-Api-Key",
        "X-Forwarded-For",
        "X-Real-Ip",
    }
)


def _safe(section_fn, request):
    """Isolate section failures: a broken section must never lose the event."""
    try:
        return section_fn(request)
    except Exception as exc:
        return {"error": f"extraction failed: {exc.__class__.__name__}"}


def _get_form(request):
    return {k: repr(v) for k, v in _filterPasswordFields(request.form.items())}


def _get_cookies(request):
    return {k: repr(v) for k, v in _filterPasswordFields(request.cookies.items())}


def _get_lazyitems(request):
    return {k: repr(v) for k, v in _filterPasswordFields(request._lazies.items())}


def _get_other(request):
    other = {}
    for k, v in _filterPasswordFields(request.other.items()):
        if k in ("PARENTS", "RESPONSE"):
            continue
        other[k] = repr(v)
    return other


def _get_request_info(request):
    environ = request.environ
    headers = {}
    filter_sensitive = not should_send_default_pii()
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-").title()
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            name = key.replace("_", "-").title()
        else:
            continue
        if filter_sensitive and name in SENSITIVE_HEADERS:
            headers[name] = "[Filtered]"
        else:
            headers[name] = str(value)
    info = {
        "headers": headers,
        "url": request.getURL(),
        "method": request.method,
        "host": environ.get("REMOTE_ADDR", ""),
    }
    query_string = environ.get("QUERY_STRING")
    if query_string:
        info["query_string"] = query_string
    return info


def _get_user(request):
    user = request.get("AUTHENTICATED_USER", None)
    if user is None:
        user = getSecurityManager().getUser()
    if user is None or user == nobody:
        return {}
    info = {"id": user.getId()}
    # getProperty exists on PAS PropertiedUser (any Plone user), not on
    # plain Zope user folder users.
    get_property = getattr(user, "getProperty", None)
    if get_property is not None:
        info["email"] = get_property("email") or ""
    return info


def request_event_processor(event, hint):
    request = getRequest()
    if request is None:
        return event
    extra = event.setdefault("extra", {})
    extra.setdefault("form", _safe(_get_form, request))
    extra.setdefault("cookies", _safe(_get_cookies, request))
    extra.setdefault("lazy items", _safe(_get_lazyitems, request))
    extra.setdefault("other", _safe(_get_other, request))
    extra.setdefault("request", _safe(_get_request_info, request))
    user_info = _safe(_get_user, request)
    if "error" in user_info:
        extra.setdefault("user", user_info)
    elif user_info:
        extra.setdefault("user", user_info)
        event.setdefault("user", user_info)
    return event
