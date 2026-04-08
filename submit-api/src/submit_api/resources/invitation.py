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
"""API endpoints for managing a invitation resource."""

from http import HTTPStatus

from flask import request
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.enums.role import ProponentPermissionsEnum
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.account import AccountCreateSchema
from submit_api.schemas.invitation import (
    CreateInvitationToExistingAccountProjectSchema, CreateNewAccountInvitationSchema, InvitationSchema)
from submit_api.services.invitation_service import InvitationService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("invitations", description="Endpoints for Invitation Management")

# Schema to handle input and output
invitation_add_schema = ApiHelper.convert_ma_schema_to_restx_model(
    API, CreateInvitationToExistingAccountProjectSchema(), "CreateInvitation"
)
invitation_response_schema = ApiHelper.convert_ma_schema_to_restx_model(
    API, InvitationSchema(), "Invitation"
)


@cors_preflight("POST, OPTIONS")
@API.route("", methods=["POST", "OPTIONS"])
class ProjectInvitationsResource(Resource):
    """Resource to create and manage invitation tokens for projects."""

    @staticmethod
    @ApiHelper.swagger_decorators(
        API, endpoint_description="Create a new invitation token"
    )
    @API.expect(invitation_add_schema)
    @API.response(
        code=HTTPStatus.CREATED,
        model=invitation_response_schema,
        description="Invitation token created",
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Invalid input data")
    @API.response(HTTPStatus.CONFLICT, "User already exists")
    @auth.require
    @auth.has_one_of_roles([ProponentPermissionsEnum.INVITE_USERS.value])
    @cross_origin(origins=allowedorigins())
    def post():
        """Generate and persist an invitation token."""
        payload = CreateInvitationToExistingAccountProjectSchema().load(request.json)

        result = InvitationService.invite_user_to_project(payload)

        if not result['success']:
            return result, HTTPStatus.CONFLICT

        # Return invitation data with the URL
        response = InvitationSchema().dump(result['invitation'])
        response['invitation_url'] = result['url']

        return response, HTTPStatus.CREATED


@cors_preflight("POST, OPTIONS")
@API.route("/account", methods=["POST", "OPTIONS"])
class AccountInvitationsResource(Resource):
    """Resource to create and manage invitation tokens for accounts."""

    @staticmethod
    @ApiHelper.swagger_decorators(
        API, endpoint_description="Create a new invitation token"
    )
    @API.expect(invitation_add_schema)
    @API.response(
        code=HTTPStatus.CREATED,
        model=invitation_response_schema,
        description="Invitation token created",
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Invalid input data")
    @API.response(HTTPStatus.CONFLICT, "User already exists")
    @auth.require
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_CREATE.value])
    @cross_origin(origins=allowedorigins())
    def post():
        """Generate and persist an invitation token."""
        payload = CreateNewAccountInvitationSchema().load(request.json)

        result = InvitationService.generate_new_entity_account_invitation(payload)

        if not result['success']:
            return result, HTTPStatus.CONFLICT

        # Return invitation data with the URL
        response = InvitationSchema().dump(result['invitation'])
        response['invitation_url'] = result['url']

        return response, HTTPStatus.CREATED


@cors_preflight("GET, DELETE, OPTIONS, POST")
@API.route("/<string:token>", methods=["GET", "DELETE", "OPTIONS", "POST"])
class InvitationDetailResource(Resource):
    """Resource to manage individual invitations by token."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get invitation by token")
    @API.response(HTTPStatus.OK, "Invitation found")
    @API.response(HTTPStatus.NOT_FOUND, "Invitation not found")
    def get(token):
        """Retrieve invitation by token."""
        invitation, valid = InvitationService.get_valid_invitation(token)
        if valid:
            return InvitationSchema().dump(invitation), HTTPStatus.OK
        return invitation, HTTPStatus.NOT_FOUND

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Revoke invitation by token")
    @API.response(HTTPStatus.NO_CONTENT, "Invitation revoked")
    @API.response(HTTPStatus.NOT_FOUND, "Invitation not found")
    @auth.require
    def delete(token):
        """Revoke an invitation token."""
        result = InvitationService.revoke_invitation(token)
        if result:
            return {}, HTTPStatus.NO_CONTENT
        return {"error": "Invitation not found or already used"}, HTTPStatus.NOT_FOUND

    @API.response(code=HTTPStatus.CREATED, model=InvitationSchema, description="User created and role assigned")
    @API.response(code=HTTPStatus.BAD_REQUEST, description="Invalid Token or Data")
    def post(self, token):
        """Accept an invitation and create a user."""
        payload = AccountCreateSchema().load(request.json)

        response = InvitationService.accept_invitation(
            token=token,
            payload=payload
        )

        if "error" in response:
            return response, HTTPStatus.BAD_REQUEST

        return response, HTTPStatus.CREATED


@cors_preflight("POST, GET, DELETE, OPTIONS")
@API.route("/id/<int:invitation_id>/resend", methods=["POST", "GET", "DELETE", "OPTIONS"])
class ResendInvitationResource(Resource):
    """Resource to resend an invitation by token."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Resend invitation by token")
    @API.response(HTTPStatus.NO_CONTENT, "Invitation resent")
    @API.response(HTTPStatus.NOT_FOUND, "Invitation not found")
    @auth.require
    @auth.has_one_of_roles([ProponentPermissionsEnum.INVITE_USERS.value])
    def post(invitation_id):
        """Resend an invitation token."""
        invitation = InvitationService.get_invitation_by_id(invitation_id)
        if invitation:
            result = InvitationService.revoke_invitation(invitation.token)
            if result:
                return {}, HTTPStatus.NO_CONTENT
        return {"error": "Invitation not found or already used"}, HTTPStatus.NOT_FOUND


@cors_preflight("GET, DELETE, OPTIONS")
@API.route("/id/<int:invitation_id>", methods=["GET", "DELETE", "OPTIONS"])
class InvitationByIdResource(Resource):
    """Resource to manage individual invitations by ID."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get invitation by ID")
    @API.response(HTTPStatus.OK, "Invitation found")
    @API.response(HTTPStatus.NOT_FOUND, "Invitation not found")
    @auth.require
    @auth.has_one_of_roles([ProponentPermissionsEnum.INVITE_USERS.value])
    def get(invitation_id):
        """Retrieve invitation by ID."""
        invitation = InvitationService.get_invitation_by_id(invitation_id)
        if invitation:
            return InvitationSchema().dump(invitation), HTTPStatus.OK
        return {"error": "Invitation not found"}, HTTPStatus.NOT_FOUND

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Revoke invitation by ID")
    @API.response(HTTPStatus.NO_CONTENT, "Invitation revoked")
    @API.response(HTTPStatus.NOT_FOUND, "Invitation not found")
    @auth.require
    @auth.has_one_of_roles([ProponentPermissionsEnum.INVITE_USERS.value])
    def delete(invitation_id):
        """Revoke an invitation by ID."""
        invitation = InvitationService.get_invitation_by_id(invitation_id)
        if invitation:
            result = InvitationService.revoke_invitation(invitation.token)
            if result:
                return {}, HTTPStatus.NO_CONTENT
        return {"error": "Invitation not found or already used"}, HTTPStatus.NOT_FOUND


@cors_preflight("PATCH, OPTIONS")
@API.route("/id/<int:invitation_id>/renew", methods=["PATCH", "OPTIONS"])
class InvitationRenewResource(Resource):
    """Resource to renew an invitation by ID."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Renew invitation by ID")
    @API.response(HTTPStatus.OK, "Invitation renewed")
    @API.response(HTTPStatus.NOT_FOUND, "Invitation not found")
    @auth.require
    @auth.has_one_of_roles([ProponentPermissionsEnum.INVITE_USERS.value])
    def patch(invitation_id):
        """Renew an invitation by ID."""
        invitation = InvitationService.get_invitation_by_id(invitation_id)
        if invitation:
            result = InvitationService.renew_invitation(invitation_id)
            if result:
                return {}, HTTPStatus.NO_CONTENT
        return {"error": "Invitation not found or already used"}, HTTPStatus.NOT_FOUND
