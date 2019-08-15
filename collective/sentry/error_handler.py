##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Site error log module.
"""

import logging
import os
import sys
import time
from random import random

from AccessControl.class_init import InitializeClass
from AccessControl.SecurityInfo import ClassSecurityInfo
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.unauthorized import Unauthorized
from Acquisition import aq_acquire
from Acquisition import aq_base
from App.Dialogs import MessageDialog
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zExceptions.ExceptionFormatter import format_exception
from zope.component import adapter
from zope.event import notify
from ZPublisher.interfaces import IPubFailure

from Products.SiteErrorLog.interfaces import ErrorRaisedEvent
from Products.SiteErrorLog.interfaces import IErrorRaisedEvent


try:
    # Python 3
    from _thread import allocate_lock
except ImportError:
    # Python 2
    from thread import allocate_lock


LOG = logging.getLogger('Zope.SiteErrorLog')

# Permission names
use_error_logging = 'Log Site Errors'
log_to_event_log = 'Log to the Event Log'

# We want to restrict the rate at which errors are sent to the Event Log
# because we know that these errors can be generated quick enough to
# flood some zLOG backends. zLOG is used to notify someone of a problem,
# not to record every instance.
# This dictionary maps exception name to a value which encodes when we
# can next send the error with that name into the event log. This dictionary
# is shared between threads and instances. Concurrent access will not
# do much harm.
_rate_restrict_pool = {}

# The number of seconds that must elapse on average between sending two
# exceptions of the same name into the the Event Log. one per minute.
_rate_restrict_period = 60

# The number of exceptions to allow in a burst before the above limit
# kicks in. We allow five exceptions, before limiting them to one per
# minute.
_rate_restrict_burst = 5

_www = os.path.join(os.path.dirname(__file__), 'www')

# temp_logs holds the logs.
temp_logs = {}  # { oid -> [ traceback string ] }

cleanup_lock = allocate_lock()

try:
    # Python 2
    bstr = basestring
except NameError:
    # Python 3
    bstr = str


class SiteErrorLog(SimpleItem):
    """Site error log class.  You can put an error log anywhere in the tree
    and exceptions in that area will be posted to the site error log.
    """
    meta_type = 'Site Error Log'
    id = 'error_log'
    zmi_icon = 'fas fa-bug'
    zmi_show_add_dialog = False

    keep_entries = 20
    copy_to_zlog = True

    security = ClassSecurityInfo()

    manage_options = (
        {'label': 'Log', 'action': 'manage_main'},
    ) + SimpleItem.manage_options

    security.declareProtected(use_error_logging, 'manage_main')  # NOQA: D001
    manage_main = PageTemplateFile('main.pt', _www)

    security.declareProtected(use_error_logging, 'showEntry')  # NOQA: D001
    showEntry = PageTemplateFile('showEntry.pt', _www)

    @security.private
    def manage_beforeDelete(self, item, container):
        if item is self:
            try:
                del container.__error_log__
            except AttributeError:
                pass

    @security.private
    def manage_afterAdd(self, item, container):
        if item is self:
            container.__error_log__ = aq_base(self)

    def _setId(self, id):
        if id != self.id:
            raise ValueError(MessageDialog(
                title='Invalid Id',
                message='Cannot change the id of a SiteErrorLog',
                action='./manage_main'))

    def _getLog(self):
        """Returns the log for this object.

        Careful, the log is shared between threads.
        """
        log = temp_logs.get(self._p_oid, None)
        if log is None:
            log = []
            temp_logs[self._p_oid] = log
        return log

    @security.protected(use_error_logging)
    def forgetEntry(self, id, REQUEST=None):
        """Removes an entry from the error log."""
        log = self._getLog()
        cleanup_lock.acquire()
        i = 0
        for entry in log:
            if entry['id'] == id:
                del log[i]
            i += 1
        cleanup_lock.release()
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(
                '%s/manage_main?manage_tabs_message='
                'Error+log+entry+was+removed.' %
                self.absolute_url())

    # Exceptions that happen all the time, so we dont need
    # to log them. Eventually this should be configured
    # through-the-web.
    _ignored_exceptions = ('Unauthorized', 'NotFound', 'Redirect')

    @security.private
    def raising(self, info):
        """Log an exception.

        Called by SimpleItem's exception handler.
        Returns the url to view the error log entry
        """
        import pdb; pdb.set_trace()
        now = time.time()
        try:
            tb_text = None
            tb_html = None

            strtype = str(getattr(info[0], '__name__', info[0]))
            if strtype in self._ignored_exceptions:
                return

            if not isinstance(info[2], bstr):
                tb_text = ''.join(
                    format_exception(*info, **{'as_html': 0}))
                tb_html = ''.join(
                    format_exception(*info, **{'as_html': 1}))
            else:
                tb_text = info[2]

            request = getattr(self, 'REQUEST', None)
            url = None
            username = None
            userid = None
            req_html = None
            try:
                strv = str(info[1])
            except Exception:
                strv = '<unprintable %s object>' % type(info[1]).__name__
            if request:
                url = request.get('URL', '?')
                usr = getSecurityManager().getUser()
                username = usr.getUserName()
                userid = usr.getId()
                try:
                    req_html = str(request)
                except Exception:
                    pass
                if strtype == 'NotFound':
                    strv = url
                    next = request['TraversalRequestNameStack']
                    if next:
                        next = list(next)
                        next.reverse()
                        strv = '%s [ /%s ]' % (strv, '/'.join(next))

            log = self._getLog()
            entry_id = str(now) + str(random())  # Low chance of collision
            log.append({
                'type': strtype,
                'value': strv,
                'time': now,
                'id': entry_id,
                'tb_text': tb_text,
                'tb_html': tb_html,
                'username': username,
                'userid': userid,
                'url': url,
                'req_html': req_html})

            cleanup_lock.acquire()
            try:
                if len(log) >= self.keep_entries:
                    del log[:-self.keep_entries]
            finally:
                cleanup_lock.release()
        except Exception:
            LOG.error('Error while logging', exc_info=sys.exc_info())
        else:
            notify(ErrorRaisedEvent(log[-1]))
            if self.copy_to_zlog:
                self._do_copy_to_zlog(now, strtype, entry_id,
                                      str(url), tb_text)
            return '%s/showEntry?id=%s' % (self.absolute_url(), entry_id)

    def _do_copy_to_zlog(self, now, strtype, entry_id, url, tb_text):
        when = _rate_restrict_pool.get(strtype, 0)
        if now > when:
            next_when = max(when,
                            now - _rate_restrict_burst * _rate_restrict_period)
            next_when += _rate_restrict_period
            _rate_restrict_pool[strtype] = next_when
            LOG.error('%s %s\n%s' % (entry_id, url, tb_text.rstrip()))

    @security.protected(use_error_logging)
    def getProperties(self):
        return {
            'keep_entries': self.keep_entries,
            'copy_to_zlog': self.copy_to_zlog,
            'ignored_exceptions': self._ignored_exceptions,
        }

    @security.protected(log_to_event_log)
    def checkEventLogPermission(self):
        if not getSecurityManager().checkPermission(log_to_event_log, self):
            raise Unauthorized('You do not have the "%s" permission.' %
                               log_to_event_log)
        return 1

    @security.protected(use_error_logging)
    def setProperties(self, keep_entries, copy_to_zlog=0,
                      ignored_exceptions=(), RESPONSE=None):
        """Sets the properties of this site error log.
        """
        copy_to_zlog = not not copy_to_zlog
        if copy_to_zlog and not self.copy_to_zlog:
            # Before turning on event logging, check the permission.
            self.checkEventLogPermission()
        self.keep_entries = int(keep_entries)
        self.copy_to_zlog = copy_to_zlog
        # filter out empty lines
        # ensure we don't save exception objects but exceptions instead
        self._ignored_exceptions = tuple(
            [_f for _f in map(str, ignored_exceptions) if _f])
        if RESPONSE is not None:
            RESPONSE.redirect(
                '%s/manage_main?manage_tabs_message=Changed+properties.' %
                self.absolute_url())

    @security.protected(use_error_logging)
    def getLogEntries(self):
        """Returns the entries in the log, most recent first.

        Makes a copy to prevent changes.
        """
        # List incomprehension ;-)
        res = [entry.copy() for entry in self._getLog()]
        res.reverse()
        return res

    @security.protected(use_error_logging)
    def getLogEntryById(self, id):
        """Returns the specified log entry.

        Makes a copy to prevent changes.  Returns None if not found.
        """
        for entry in self._getLog():
            if entry['id'] == id:
                return entry.copy()
        return None

    @security.protected(use_error_logging)
    def getLogEntryAsText(self, id, RESPONSE=None):
        """Returns the specified log entry.

        Makes a copy to prevent changes.  Returns None if not found.
        """
        entry = self.getLogEntryById(id)
        if entry is None:
            return 'Log entry not found or expired'
        if RESPONSE is not None:
            RESPONSE.setHeader('Content-Type', 'text/plain')
        return entry['tb_text']


InitializeClass(SiteErrorLog)


def manage_addErrorLog(dispatcher, RESPONSE=None):
    """Add a site error log to a container."""
    log = SiteErrorLog()
    dispatcher._setObject(log.id, log)
    if RESPONSE is not None:
        RESPONSE.redirect(
            dispatcher.DestinationURL()
            + '/manage_main?manage_tabs_message=Error+Log+Added.')


@adapter(IPubFailure)
def IPubFailureSubscriber(event):
    """ Handles an IPubFailure event triggered by the WSGI Publisher.
        This handler forwards the event to the SiteErrorLog object
        closest to the published object that the error occured with,
        it logs no error if no published object was found.
    """

    request = event.request
    published = request.get('PUBLISHED')
    if published is None:  # likely a traversal problem
        parents = request.get('PARENTS')
        if parents:
            # partially emulate successful traversal
            published = request['PUBLISHED'] = parents.pop(0)
    if published is None:
        return

    published = getattr(published, '__self__', published)  # method --> object


    try:
        error_log = aq_acquire(published, '__error_log__', containment=1)
    except AttributeError:
        pass
    else:
        error_log.raising(event.exc_info)

@adapter(IErrorRaisedEvent)
def sentry_handler(event):
    import pdb; pdb.set_trace()
