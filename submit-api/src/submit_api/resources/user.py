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

from flask import g
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.exceptions import ResourceNotFoundError
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.user import UserSchema
from submit_api.services.user_service import UserService
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("users", description="Endpoints for Account Management")
"""Custom exception messages
"""

user_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, UserSchema(), "User"
)


@cors_preflight("GET, OPTIONS, POST")
@API.route("/me", methods=["GET", "POST", "OPTIONS"])
class CurrentUser(Resource):
    """Resource for getting current authenticated user."""

    @staticmethod
    @ApiHelper.swagger_decorators(
        API,
        endpoint_description="Get or create current user, auto-provision staff if they have valid roles"
    )
    @API.response(code=200, model=user_model, description="User found")
    @API.response(code=201, model=user_model, description="User created")
    @API.response(404, "Not Found")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def post():
        """Get or create current authenticated user."""
        # Get token info from flask.g (set by @auth.require decorator)
        token_info = g.get('token_info')
        guid = token_info.get('preferred_username') if token_info else None

        if not guid:
            raise ResourceNotFoundError("User GUID not found in token")

        # Use get_or_provision method which will auto-create staff users with valid roles
        user = UserService.get_or_provision_by_auth_guid(guid, token_info)

        return UserSchema().dump(user), HTTPStatus.OK


@cors_preflight("GET, OPTIONS")
@API.route("/guid/<string:guid>", methods=["GET", "OPTIONS"])
@API.doc(params={"guid": "The user global unique identifier"})
class User(Resource):
    """Resource for managing a single account"""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch a user by guid")
    @API.response(code=200, model=user_model, description="Success")
    @API.response(404, "Not Found")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(guid):
        """Fetch an account by id."""
        user = UserService.get_by_auth_guid(guid)
        if not user:
            raise ResourceNotFoundError(f"User with GUID '{guid}' not found")
        return UserSchema().dump(user), HTTPStatus.OK
