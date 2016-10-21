from __future__ import unicode_literals, division, absolute_import
from builtins import *  # pylint: disable=unused-import, redefined-builtin

import logging

from flexget import plugin
from flexget.event import event
from flexget.utils import json
from flexget.utils.template import RenderError
from flexget.config_schema import one_or_more

log = logging.getLogger('notify_join')

join_api_url = 'https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush'


class NotifyJoin(object):
    """
    Example::

      notify_join:
        [api_key: <API_KEY> (your join api key. Only required for 'group' notifications)]
        [group: <GROUP_NAME> (name of group of join devices to notify. 'all', 'android', etc.)
        [device: <DEVICE_ID> (can also be a list of device ids)]
        [title: <NOTIFICATION_TITLE>] (default: "{{task}} - Download started" -- accepts Jinja2)
        [body: <NOTIFICATION_TEXT>] (default: "{{series_name}} {{series_id}}" -- accepts Jinja2)

    Configuration parameters are also supported from entries (eg. through set).
    """
    default_body = ('{% if series_name is defined %}{{tvdb_series_name|d(series_name)}} {{series_id}} '
                    '{{tvdb_ep_name|d('')}}{% elif imdb_name is defined %}{{imdb_name}} '
                    '{{imdb_year}}{% else %}{{title}}{% endif %}')
    schema = {
        'type': 'object',
        'properties': {
            'api_key': {'type': 'string'},
            'group': {
                'type': 'string',
                'enum': ['all', 'android', 'chrome', 'windows10', 'phone', 'tablet', 'pc']
            },
            'device': one_or_more({'type': 'string'}),
            'title': {'type': 'string', 'default': '{{task}} - Download started'},
            'body': {'type': 'string', 'default': default_body},
            'url': {'type': 'string'},
        },
        'dependencies': {
            'group': ['api_key']
        },
        'error_dependencies': '`api_key` is required to use Join `group` notifications',
        'oneOf': [
            {'required': ['device']},
            {'required': ['group']},
        ],
        'error_oneOf': 'Either a `device` to notify, or a `group` of devices must be specified.',
        'additionalProperties': False
    }

    # Run last to make sure other outputs are successful before sending notification
    @plugin.priority(0)
    def on_task_output(self, task, config):
        global_data = {}
        # Figure out which devices to notify
        if 'group' in config:
            global_data['apikey'] = config['api_key']
            global_data['deviceId'] = 'group.' + config['group']
        else:
            if isinstance(config['device'], list):
                global_data['deviceIds'] = ','.join(config['device'])
            else:
                global_data['deviceId'] = config['device']
        for entry in task.accepted:
            data = global_data.copy()

            # Attempt to render the title field
            try:
                data['title'] = entry.render(config['title'])
            except RenderError as e:
                log.warning('Problem rendering `title`: %s' % e)
                data['title'] = 'Download started'

            # Attempt to render the body field
            try:
                data['text'] = entry.render(config['body'])
            except RenderError as e:
                log.warning('Problem rendering `body`: %s' % e)
                data['text'] = entry['title']

            # Attempt to render the url field
            if config.get('url'):
                try:
                    data['url'] = entry.render(config['url'])
                except RenderError as e:
                    log.warning('Problem rendering `url`: %s' % e)

            # Check for test mode
            if task.options.test:
                log.info('Test mode. Join notification would be:')
                log.info('    Title: %s', data['title'])
                log.info('    Body: %s', data['text'])
                if data.get('url'):
                    log.info('    URL: %s' % data['url'])
                log.debug('    Raw Data: %s' % json.dumps(data))
                # Test mode.  Skip remainder.
                continue

            # Make the request
            response = task.requests.get(join_api_url, params=data)

            # Check if it succeeded
            request_status = response.status_code

            # error codes (these haven't really been tested, just copied from pushbullet plugin)
            if request_status == 200:
                log.debug('Join notification sent')
            elif request_status == 500:
                log.warning('Join notification failed, Join API having issues')
            elif request_status >= 400:
                error = 'Unknown error'
                if response.content:
                    try:
                        error = response.json()['error']['message']
                    except ValueError as e:
                        error = 'Unknown Error (Invalid JSON returned): %s' % e
                log.error('Join API error: %s' % error)
            else:
                log.error('Unknown error when sending Join notification')


@event('plugin.register')
def register_plugin():
    plugin.register(NotifyJoin, 'notify_join', api_ver=2)
