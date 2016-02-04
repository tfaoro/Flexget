from __future__ import unicode_literals, division, absolute_import

import copy
from math import ceil
from operator import itemgetter
from urllib import unquote

from flask import jsonify, request
from flask_restplus import inputs

from flexget.api import api, APIResource
from flexget.plugins.filter import seen

seen_api = api.namespace('seen', description='Managed Flexget seen entries and fields')

PLUGIN_TASK_NAME = 'seen_plugin_API'  # Name of task to use when adding entries via API

default_error_schema = {
    'type': 'object',
    'properties': {
        'status': {'type': 'string'},
        'message': {'type': 'string'}
    }
}

empty_response = api.schema('empty', {'type': 'object'})

default_error_schema = api.schema('default_error_schema', default_error_schema)

seen_field_object = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'field': {'type': 'string'},
        'value': {'type': 'string'},
        'added': {'type': 'string'},
        'seen_entry_id': {'type': 'integer'}
    }
}

seen_object = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'title': {'type': 'string'},
        'reason': {'type': 'string'},
        'task': {'type': 'string'},
        'added': {'type': 'string'},
        'local': {'type': 'boolean'},
        'fields': {'type': 'array', 'items': seen_field_object}
    }
}
seen_object_schema = api.schema('seen_object_schema', seen_object)

# Copy inout schema from seen object and manipulate to get desired fields
seen_object_input_schema = copy.deepcopy(seen_object)

# Removing unneeded fields
del seen_object_input_schema['properties']['id']
del seen_object_input_schema['properties']['added']

# Get dict and not array of dicts
seen_object_input_schema['properties']['fields'] = {'type': 'object'}

# Set default local status to False
seen_object_input_schema['properties']['local'] = {'type': 'boolean', 'default': False}

# Add JSON schema validation fields
seen_object_input_schema.update({'required': ['title', 'fields'],
                                 'additional_properties': False})

seen_object_input_schema = api.schema('seen_object_input_schema', seen_object_input_schema)

seen_search_schema = {
    'type': 'object',
    'properties': {
        'seen_entries': {
            'type': 'array',
            'items': seen_object
        },
        'number_of_seen_entries': {'type': 'integer'},
        'total_number_of_pages': {'type': 'integer'},
        'page_number': {'type': 'integer'}
    }
}
seen_search_schema = api.schema('seen_search_schema', seen_search_schema)

seen_search_parser = api.parser()
seen_search_parser.add_argument('value', help='Search by any field value or leave empty to get entries')
seen_search_parser.add_argument('page', type=int, default=1, help='Page number')
seen_search_parser.add_argument('max', type=int, default=50, help='Seen entries per page')
seen_search_parser.add_argument('is_seen_local', type=inputs.boolean, default=None,
                                help='Filter results by seen locality.')
seen_search_parser.add_argument('sort_by', choices=('title', 'task', 'added', 'local', 'id'), default='added',
                                help="Sort response by attribute")
seen_search_parser.add_argument('order', choices=('asc', 'desc'), default='desc', help='Sorting order.')

seen_delete_parser = api.parser()
seen_delete_parser.add_argument('value', help='Delete by value or leave empty to delete all. BE CAREFUL WITH THIS')
seen_delete_parser.add_argument('is_seen_local', type=inputs.boolean, default=None,
                                help='Filter results by seen locality.')


@seen_api.route('/')
@api.doc(description='Get, delete or create seen entries')
class SeenSearchAPI(APIResource):
    @api.response(404, 'Page does not exist', model=default_error_schema)
    @api.response(200, 'Successfully retrieved seen objects', seen_search_schema)
    @api.doc(parser=seen_search_parser)
    def get(self, session):
        """ Search for seen entries """
        args = seen_search_parser.parse_args()
        value = args['value']
        page = args['page']
        max_results = args['max']
        is_seen_local = args['is_seen_local']
        sort_by = args['sort_by']
        order = args['order']

        # Handles default if it explicitly called
        if order == 'desc':
            order = True
        else:
            order = False

        # Unquotes and prepares value for DB lookup
        if value:
            value = unquote(value)
            value = '%{0}%'.format(value)

        raw_seen_entries_list = seen.search(value=value, status=is_seen_local, session=session)
        converted_seen_entry_list = [entry.to_dict() for entry in raw_seen_entries_list]
        sorted_seen_entries_list = sorted(converted_seen_entry_list, key=itemgetter(sort_by), reverse=order)

        # Pagination
        count = len(sorted_seen_entries_list)

        pages = int(ceil(count / float(max_results)))

        # Invalid page request
        if page > pages and pages != 0:
            return {'status': 'error',
                    'message': 'page %s does not exist' % page}, 404

        start = (page - 1) * max_results
        finish = start + max_results
        if finish > count:
            finish = count

        paginated_seen_entries = []
        for seen_entry_num in range(start, finish):
            paginated_seen_entries.append(sorted_seen_entries_list[seen_entry_num])

        return jsonify({
            'seen_entries': paginated_seen_entries,
            'number_of_seen_entries': count,
            'page_number': page,
            'total_number_of_pages': pages
        })

    example = "fields: {'url': 'http://123.com', 'title': 'A.Torrent', 'imdb_id': 'tt1234567'"

    @api.response(500, 'A matching seen object is already added', model=default_error_schema)
    @api.response(201, 'Successfully added new seen object', seen_object_schema)
    @api.validate(model=seen_object_input_schema,
                  description='Fields attribute takes a dict to add as seen entry fields, '
                              'for example: {0}'.format(example))
    def post(self, session):
        """ Manually add entries to seen plugin """
        data = request.json
        kwargs = {
            'title': data.get('title'),
            'task_name': data.get('task', PLUGIN_TASK_NAME),
            'fields': data.get('fields'),
            'reason': data.get('reason'),
            'local': data.get('local', False),
            'session': session
        }
        values = [value for value in kwargs['fields'].values()]
        exist = seen.search_by_field_values(field_value_list=values, task_name=PLUGIN_TASK_NAME, local=kwargs['local'],
                                            session=session)
        if exist:
            return {'status': 'error',
                    'message': "Seen entry matching the value '{0}' is already added".format(exist.value)}, 400

        seen_entry = seen.add(**kwargs)
        return jsonify(seen_entry), 201

    @api.response(500, 'Delete process failed', model=default_error_schema)
    @api.response(200, 'Successfully delete all entries', empty_response)
    @api.doc(parser=seen_delete_parser)
    def delete(self, session):
        """ Delete seen entries """
        args = seen_delete_parser.parse_args()
        value = args['value']
        is_seen_local = args['is_seen_local']

        if value:
            value = unquote(value)
            value = '%' + value + '%'
        seen_entries_list = seen.search(value, is_seen_local, session)

        for entry in seen_entries_list:
            try:
                seen.forget_by_id(entry.id)
            except ValueError as e:
                return {'status': 'error',
                        'message': 'Could not delete entry ID {0}'.format(entry.id)}, 500
        return {}


@seen_api.route('/<int:seen_entry_id>')
@api.doc(params={'seen_entry_id': 'ID of seen entry'}, description='Delete a specific seen entry via its ID')
@api.response(500, 'Delete process failed', model=default_error_schema)
@api.response(200, 'Successfully deleted entry', empty_response)
class SeenSearchAPI(APIResource):
    def delete(self, seen_entry_id, session):
        """ Delete seen entry by ID """
        try:
            seen.forget_by_id(seen_entry_id)
        except ValueError as e:
            return {'status': 'error',
                    'message': 'Could not delete entry ID {0}'.format(seen_entry_id)}, 500
        return {}
