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

from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.exceptions import ResourceNotFoundError
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.account import AccountCreateSchema, AccountSchema
from submit_api.schemas.package import AccountPackageSchema
from submit_api.services.account_service import AccountService
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("accounts", description="Endpoints for Account Management")
"""Custom exception messages
"""

account_create_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, AccountCreateSchema(), "Account Create"
)
account_list_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, AccountSchema(), "Account"
)
account_package_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, AccountPackageSchema(), "Account Package"
)


@cors_preflight("GET, OPTIONS, POST")
@API.route("", methods=["POST", "GET", "OPTIONS"])
class Accounts(Resource):
    """Resource for managing accounts."""

    @staticmethod
    @API.response(code=HTTPStatus.OK, description="Success", model=[account_list_model])
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch all accounts")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get():
        """Fetch all accounts."""
        accounts = AccountService.get_all_accounts()
        accounts_list_schema = AccountSchema(many=True)
        return accounts_list_schema.dump(accounts), HTTPStatus.OK

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Create an account")
    @API.expect(account_create_model)
    @API.response(code=HTTPStatus.CREATED, model=account_list_model, description="Account Created")
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def post():
        """Create an account."""
        account_data = AccountCreateSchema().load(API.payload)
        created_account = AccountService.create_account(account_data)
        return AccountSchema().dump(created_account), HTTPStatus.CREATED


@cors_preflight("GET, OPTIONS")
@API.route("/proponent/<int:proponent_id>", methods=["GET", "OPTIONS"])
@API.doc(params={"proponent_id": "The account identifier"})
class User(Resource):
    """Resource for managing a single account"""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch a account by proponent id")
    @API.response(code=200, model=account_list_model, description="Success")
    @API.response(404, "Not Found")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(proponent_id):
        """Fetch an account by proponent id."""
        account = AccountService.get_account_by_proponent_id(proponent_id)
        if not account:
            raise ResourceNotFoundError(f"Account with proponent {proponent_id} not found")
        return AccountSchema().dump(account), HTTPStatus.OK


@cors_preflight("GET, OPTIONS")
@API.route(
    "/<int:account_id>/packages",
    methods=["GET", "OPTIONS"],
)
class AccountPackages(Resource):
    """Resource for managing account packages."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get packages by account_id")
    @API.response(
        code=HTTPStatus.OK, model=account_package_model, description="Get packages"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(account_id):
        """Get all account packages."""
        account_packages = AccountService.get_all_account_packages(account_id)
        return AccountPackageSchema(many=True).dump(account_packages), HTTPStatus.OK
