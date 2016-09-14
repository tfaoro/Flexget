from __future__ import unicode_literals, division, absolute_import
from builtins import *  # pylint: disable=unused-import, redefined-builtin

from flask import request
from flask_login import current_user

from flexget.api import api, BadRequest, base_message_schema, success_response
from flexget.api.models import APIResource
from flexget.webserver import change_password, generate_token, WeakPassword

user_api = api.namespace('user', description='Manage user login credentials')


class ObjectsContainer(object):
    user_password_input = {
        'type': 'object',
        'properties': {
            'password': {'type': 'string'}
        },
        'required': ['password'],
        'additionalProperties': False
    }

    user_token_response = {
        'type': 'object',
        'properties': {
            'token': {'type': 'string'}
        }
    }


user_password_input_schema = api.schema('user_password_input', ObjectsContainer.user_password_input)
user_token_response_schema = api.schema('user_token_response', ObjectsContainer.user_token_response)


@user_api.route('/')
@api.doc('Change user password')
class UserManagementAPI(APIResource):
    @api.validate(model=user_password_input_schema, description='Password change schema')
    @api.response(BadRequest)
    @api.response(200, 'Success', model=base_message_schema)
    @api.doc(description='Change user password. A medium strength password is required.'
                         ' See https://github.com/lepture/safe for reference')
    def put(self, session=None):
        """ Change user password """
        user = current_user
        data = request.json
        try:
            change_password(username=user.name, password=data.get('password'), session=session)
        except WeakPassword as e:
            raise BadRequest(e.value)
        return success_response('Successfully changed user password')


@user_api.route('/token/')
@api.doc('Change user token')
class UserManagementTokenAPI(APIResource):
    @api.response(200, 'Successfully changed user token', user_token_response_schema)
    @api.doc(description='Get new user token')
    def get(self, session=None):
        """ Change current user token """
        token = generate_token(username=current_user.name, session=session)
        return {'token': token}
