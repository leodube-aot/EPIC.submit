# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API endpoints for managing an account resource."""

from http import HTTPStatus

from flask import jsonify, request
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.exceptions import PermissionDeniedError, ResourceNotFoundError
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.account_user import AccountUserSchema, EditRoleSchema, EditTermsOfServiceSchema
from submit_api.services.account_user_service import AccountUserService
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("accounts", description="Endpoints for Account User Management")
"""Custom exception messages
"""

account_user_list_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, AccountUserSchema(), "AccountUser"
)


@cors_preflight("GET, OPTIONS")
@API.route("/<int:account_id>/users", methods=["GET", "OPTIONS"])
@API.doc(params={
    "account_id": "The account identifier",
    "include_invitees": "Include invitees (true/false)",
    "include_roles": "Include roles (true/false)"
})
class AccountUsers(Resource):
    """Resource for listing users associated with an account."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch all users of an account")
    @API.response(code=HTTPStatus.OK, description="Success", model=[account_user_list_model])
    @API.response(HTTPStatus.NOT_FOUND, "Account not found")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(account_id):
        """Fetch all users of a specific account."""
        include_roles = request.args.get("include_roles", "false").lower() == "true"
        include_invitees = request.args.get("include_invitees", "false").lower() == "true"

        users = AccountUserService.get_users_by_account_projects(account_id, include_roles, include_invitees)
        if not users:
            return {"message": "No users found"}, HTTPStatus.NOT_FOUND

        users_list_schema = AccountUserSchema(many=True)
        return users_list_schema.dump(users), HTTPStatus.OK


@cors_preflight("GET, PATCH, OPTIONS")
@API.route("/user/<string:guid>", methods=["GET", "PATCH", "OPTIONS"])
class AccountUser(Resource):
    """Resource for fetching or editing a user."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch an user for a user id")
    @API.response(code=HTTPStatus.OK, description="Success", model=[account_user_list_model])
    @API.response(HTTPStatus.NOT_FOUND, "User not found")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(guid):
        """Fetch an user for a user id."""
        user = AccountUserService.get_account_user(guid)
        if not user:
            return {"message": f"No user found for user id {guid}"}, HTTPStatus.NOT_FOUND
        return AccountUserSchema().dump(user), HTTPStatus.OK

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Edit a account user")
    @API.expect(account_user_list_model)
    @API.response(
        code=HTTPStatus.OK, model=account_user_list_model, description="Account user"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def patch(guid):
        """Edit a account user."""
        edit_account_user_data = AccountUserSchema().load(API.payload)
        edited_account_user = AccountUserService.update_account_user(guid, edit_account_user_data)
        return AccountUserSchema().dump(edited_account_user), HTTPStatus.OK


@cors_preflight("GET, OPTIONS")
@API.route("/users/<int:account_user_id>", methods=["GET", "OPTIONS"])
class AccountUserById(Resource):
    """Resource for fetching a user by account_user id."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch a user by account_user id")
    @API.response(code=HTTPStatus.OK, description="Success", model=account_user_list_model)
    @API.response(HTTPStatus.NOT_FOUND, "User not found")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(account_user_id):
        """Fetch a user by account_user id."""
        user = AccountUserService.get_account_user_by_id(account_user_id)
        if not user:
            return {"message": f"No user found for account_user id {account_user_id}"}, HTTPStatus.NOT_FOUND
        return AccountUserSchema().dump(user), HTTPStatus.OK


@cors_preflight("PATCH, OPTIONS")
@API.route("/user/<int:account_user_id>/role", methods=["PATCH", "OPTIONS"])
class EditUserRole(Resource):
    """Resource for editing a user's role."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Edit a user's role")
    @API.expect(account_user_list_model)
    @API.response(
        code=HTTPStatus.OK, model=account_user_list_model, description="Account user"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def patch(account_user_id):
        """Edit a user's role."""
        user_guid = auth.preferred_username
        new_role_data = EditRoleSchema().load(API.payload)
        try:
            updated_role_data = AccountUserService.update_role(user_guid, account_user_id, new_role_data)
            return AccountUserSchema().dump(updated_role_data), HTTPStatus.OK
        except PermissionDeniedError as e:
            return jsonify({"message": str(e)}), HTTPStatus.FORBIDDEN

        except ResourceNotFoundError as e:
            return jsonify({"error": str(e)}), HTTPStatus.NOT_FOUND


@cors_preflight("PATCH, OPTIONS")
@API.route("/user/<string:account_user_id>/status", methods=["PATCH", "OPTIONS"])
class EditUserStatus(Resource):
    """Resource for editing a user's status."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Edit a user's status")
    @API.expect(account_user_list_model)
    @API.response(
        code=HTTPStatus.OK, model=account_user_list_model, description="Account user"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def patch(account_user_id):
        """Edit a user's status."""
        user_guid = auth.preferred_username
        try:
            data = request.get_json()
            if data.get('active', None) is None:
                return {'message': 'active field is required'}, HTTPStatus.BAD_REQUEST
            updated_status_data = AccountUserService.reactivate_deactivate_user(
                user_guid, account_user_id, active=data.get('active'))
            return AccountUserSchema().dump(updated_status_data), HTTPStatus.OK
        except PermissionDeniedError as e:
            return jsonify({"message": str(e)}), HTTPStatus.FORBIDDEN

        except ResourceNotFoundError as e:
            return jsonify({"error": str(e)}), HTTPStatus.NOT_FOUND


@cors_preflight("PATCH, OPTIONS")
@API.route("/user/<string:account_user_id>/terms-of-service", methods=["PATCH", "OPTIONS"])
class EditUserTermsOfService(Resource):
    """Resource for editing a user's terms of service."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Edit a user's terms of service")
    @API.expect(account_user_list_model)
    @API.response(
        code=HTTPStatus.OK, model=account_user_list_model, description="Account user"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def patch(account_user_id):
        """Edit a user's terms of service."""
        update_data = EditTermsOfServiceSchema().load(API.payload)
        try:
            updated_user_terms_of_service = AccountUserService.record_user_terms_of_service(
                account_user_id, update_data)
            return AccountUserSchema().dump(updated_user_terms_of_service), HTTPStatus.OK
        except PermissionDeniedError as e:
            return jsonify({"message": str(e)}), HTTPStatus.FORBIDDEN

        except ResourceNotFoundError as e:
            return jsonify({"error": str(e)}), HTTPStatus.NOT_FOUND
