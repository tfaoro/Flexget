from __future__ import unicode_literals, division, absolute_import
from builtins import *  # noqa pylint: disable=unused-import, redefined-builtin

import logging
import xml.etree.ElementTree as ET
import requests

from flexget import plugin
from flexget.config_schema import one_or_more
from flexget.event import event
from requests.exceptions import RequestException

__name__ = 'notifymyandroid'
log = logging.getLogger(__name__)

NOTIFYMYANDROID_URL = 'https://www.notifymyandroid.com/publicapi/notify'


class NotifyMyAndroidNotifier(object):
    """
    Example::

      notifymyandroid:
        apikey: xxxxxxx
        [application: application name, default FlexGet]
        [event: event title, default New Release]
        [priority: -2 - 2 (2 = highest), default 0]

    Configuration parameters are also supported from entries (eg. through set).
    """

    schema = {
        'type': 'object',
        'properties': {
            'apikey': one_or_more({'type': 'string'}),
            'application': {'type': 'string', 'default': 'FlexGet'},
            'title': {'type': 'string'},
            'message': {'type': 'string'},
            'priority': {'type': 'integer', 'default': 0},
            'developerkey': {'type': 'string'},
            'url': {'type': 'string'},
            'html': {'type': 'boolean'},
            'template': {'type': 'string', 'format': 'template'}
        },
        'required': ['apikey'],
        'additionalProperties': False
    }

    def notify(self, data):
        # Handle multiple API keys
        if isinstance(data['apikey'], list):
            data['apikey'] = ','.join(data['apikey'])

        data['event'] = data.pop('title')
        data['description'] = data.pop('message')

        # Special case for html handling
        html = data.pop('html', None)
        if html:
            data['content-type'] = 'text/html'

        try:
            response = requests.post(NOTIFYMYANDROID_URL, data=data)
        except RequestException as e:
            log.error('Could not connect to notifymyandroid: %s', e.args[0])
            return
        request_status = ET.fromstring(response.content)
        error = request_status.find('error')
        if error is not None:
            log.error('Could not send notification: %s', error.text)
        else:
            success = request_status.find('success').attrib
            log.verbose('notifymyandroid notification sent. Notifications remaining until next reset: %s. '
                        'Next reset will occur in %s minutes', success['remaining'], success['resettimer'])

    # Run last to make sure other outputs are successful before sending notification
    @plugin.priority(0)
    def on_task_output(self, task, config):
        # Send default values for backwards compatibility
        notify_config = {
            'to': [{__name__: config}],
            'scope': 'entries',
            'what': 'accepted'
        }
        plugin.get_plugin_by_name('notify').instance.send_notification(task, notify_config)


@event('plugin.register')
def register_plugin():
    plugin.register(NotifyMyAndroidNotifier, __name__, api_ver=2, groups=['notifiers'])