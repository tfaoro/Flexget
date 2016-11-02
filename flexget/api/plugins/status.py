from __future__ import unicode_literals, division, absolute_import
from builtins import *  # pylint: disable=unused-import, redefined-builtin

from datetime import datetime, timedelta

from flask import jsonify, request
from flask_restplus import inputs
from flexget.api.core.tasks import tasks_api
from flexget.plugins.operate.status import StatusTask, get_executions_by_task_id
from math import ceil

from flexget.api import api, APIResource
from sqlalchemy.orm.exc import NoResultFound
from flexget.api.app import NotFoundError, etag, pagination_headers

status_api = api.namespace('status', description='View and manage task execution status')


class ObjectsContainer(object):
    task_status_execution_schema = {
        'type': 'object',
        'properties': {
            'abort_reason': {'type': ['string', 'null']},
            'accepted': {'type': 'integer'},
            'end': {'type': 'string', 'format': 'date-time'},
            'failed': {'type': 'integer'},
            'id': {'type': 'integer'},
            'produced': {'type': 'integer'},
            'rejected': {'type': 'integer'},
            'start': {'type': 'string', 'format': 'date-time'},
            'succeeded': {'type': 'boolean'},
            'task_id': {'type': 'integer'}
        },
        'required': ['abort_reason', 'accepted', 'end', 'failed', 'id', 'produced', 'rejected', 'start', 'succeeded',
                     'task_id'],
        'additionalProperties': False
    }

    executions_list = {'type': 'array', 'items': task_status_execution_schema},

    task_status_schema = {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'}
        },
        'required': ['executions', 'id', 'name', 'total_executions'],
        'additionalProperties': False
    }

    task_status_list_schema = {'type': 'array', 'items': task_status_schema}


task_status = api.schema('tasks.tasks_status', ObjectsContainer.task_status_schema)
task_status_list = api.schema('tasks.tasks_status_list', ObjectsContainer.task_status_list_schema)
task_executions = api.schema('tasks.tasks_executions_list', ObjectsContainer.executions_list)


@tasks_api.route('/status/')
@status_api.route('/')
class TasksStatusAPI(APIResource):
    @etag
    @api.response(200, model=task_status_list)
    def get(self, session=None):
        """Get status tasks"""
        return jsonify([task.to_dict() for task in session.query(StatusTask).all()])


@tasks_api.route('/status/<int:task_id>/')
@status_api.route('/<int:task_id>/')
@api.doc(params={'task_id': 'ID of the status task'})
class TaskStatusAPI(APIResource):
    @etag
    @api.response(200, model=task_status)
    @api.response(NotFoundError)
    def get(self, task_id, session=None):
        """Get status task by ID"""
        try:
            task = session.query(StatusTask).filter(StatusTask.id == task_id).one()
        except NoResultFound:
            raise NotFoundError('task status with id %d not found' % task_id)
        return jsonify(task.to_dict())


default_start_date = (datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d')

executions_parser = api.parser()
executions_parser.add_argument('succeeded', type=inputs.boolean, default=True, help='Filter by success status')
executions_parser.add_argument('produced', type=inputs.boolean, default=True, store_missing=False,
                               help='Filter by tasks that produced entries')
executions_parser.add_argument('start_date', type=inputs.datetime_from_iso8601, default=default_start_date,
                               help='Filter by minimal start date. Example: \'2012-01-01\'. Default is 1 week ago.')
executions_parser.add_argument('end_date', type=inputs.datetime_from_iso8601,
                               help='Filter by maximal end date. Example: \'2012-01-01\'')

sort_choices = ('start', 'end', 'succeeded', 'produced', 'accepted', 'rejected', 'failed', 'abort_reason')
executions_parser = api.pagination_parser(executions_parser, sort_choices=sort_choices)


@tasks_api.route('/status/<int:task_id>/executions/')
@status_api.route('/<int:task_id>/executions/')
@api.doc(parser=executions_parser, params={'task_id': 'ID of the status task'})
class TaskStatusExecutionsAPI(APIResource):
    @etag
    @api.response(200, model=task_executions)
    @api.response(NotFoundError)
    def get(self, task_id, session=None):
        """Get task executions by ID"""
        try:
            task = session.query(StatusTask).filter(StatusTask.id == task_id).one()
        except NoResultFound:
            raise NotFoundError('task status with id %d not found' % task_id)

        args = executions_parser.parse_args()

        # Pagination and sorting params
        page = args['page']
        per_page = args['per_page']
        sort_by = args['sort_by']
        sort_order = args['order']
        succeeded = args.get('succeeded')
        produced = args.get('produced')
        start_date = args.get('start_date')
        end_date = args.get('end_date')

        if per_page > 100:
            per_page = 100

        start = per_page * (page - 1)
        stop = start + per_page
        descending = bool(sort_order == 'desc')

        kwargs = {
            'start': start,
            'stop': stop,
            'task_id': task_id,
            'order_by': sort_by,
            'descending': descending,
            'succeeded': succeeded,
            'produced': produced,
            'start_date': start_date,
            'end_date': end_date,
            'session': session
        }

        total_items = task.executions.count()

        if not total_items:
            return jsonify([])

        executions = [e.to_dict() for e in get_executions_by_task_id(**kwargs)]

        total_pages = int(ceil(total_items / float(per_page)))

        if page > total_pages:
            raise NotFoundError('page %s does not exist' % page)

        # Actual results in page
        actual_size = min(len(executions), per_page)

        # Get pagination headers
        pagination = pagination_headers(total_pages, total_items, actual_size, request)

        # Create response
        rsp = jsonify(executions)

        # Add link header to response
        rsp.headers.extend(pagination)
        return rsp
