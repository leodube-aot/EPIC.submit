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

from flask import request
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.exceptions import ResourceNotFoundError
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.staff_user import CreateStaffUserRequest, StaffUserSchema
from submit_api.services.staff_user_service import StaffUserService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("staff-user", description="Endpoints for Staff Management")
"""Custom exception messages
"""

user_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, StaffUserSchema(), "Staff User"
)

create_user_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, CreateStaffUserRequest(), "Create Staff User Request"
)


@cors_preflight("GET, OPTIONS")
@API.route("/<string:guid>", methods=["GET", "OPTIONS"])
@API.doc(params={"guid": "The user global unique identifier"})
class StaffUser(Resource):
    """Resource for managing a single account"""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch a staff by guid")
    @API.response(code=200, model=user_model, description="Success")
    @API.response(404, "Not Found")
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_VIEW.value])
    @cross_origin(origins=allowedorigins())
    def get(guid):
        """Fetch a staff by id."""
        staff = StaffUserService.get_staff_by_id(guid)
        if not staff:
            raise ResourceNotFoundError(f"User with guid {guid} not found")
        return StaffUserSchema().dump(staff), HTTPStatus.OK


@cors_preflight("POST, OPTIONS")
@API.route("/", methods=["POST", "OPTIONS"])
class StaffUserCreate(Resource):
    """Resource for creating a staff user."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Create a staff user and assign Keycloak role")
    @API.expect(create_user_model, validate=True)
    @API.response(code=201, model=user_model, description="User created and role assigned")
    @API.response(code=400, description="Invalid input")
    @API.response(code=500, description="Internal server error")
    @auth.has_one_of_staff_roles([EpicSubmitRole.MANAGE_USERS.value])
    @cross_origin(origins=allowedorigins())
    def post():
        """Create a staff user and assign a Keycloak role."""
        request_data = request.get_json()
        email = request_data.get("email")
        group_name = request_data.get("group_name")

        if not email or not group_name:
            return {"message": "Both 'email' and 'role' are required."}, HTTPStatus.BAD_REQUEST

        try:
            StaffUserService.create_and_assign_group(email=email, group_name=group_name)
            return {"message": f"User '{email}' created and assigned role '{group_name}'."}, HTTPStatus.CREATED
        except Exception as e:  # pylint:disable=broad-exception-caught  # noqa: B902
            return {"message": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR
