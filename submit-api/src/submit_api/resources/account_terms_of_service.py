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
"""API endpoints for managing terms of service."""

from http import HTTPStatus

from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.exceptions import ResourceNotFoundError
from submit_api.models.account_terms_of_service import TermsOfService as TermsOfServiceModel
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.account_terms_of_service import TermsOfServiceSchema
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("terms-of-service", description="Endpoints for Terms of service")
"""Custom exception messages
"""

terms_of_service_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, TermsOfServiceSchema(), "TermsOfService"
)


@cors_preflight("GET, POST, OPTIONS")
@API.route("", methods=["GET", "POST", "OPTIONS"])
class TermsOfService(Resource):
    """Resource for managing terms of service"""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Fetch active terms of service")
    @API.response(code=200, model=terms_of_service_model, description="Success")
    @API.response(404, "Not Found")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get():
        """Fetch active terms of service."""
        terms_of_service = TermsOfServiceModel.get_active_terms_of_service()
        if not terms_of_service:
            raise ResourceNotFoundError("No active terms of service found")
        return TermsOfServiceSchema().dump(terms_of_service), HTTPStatus.OK

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Create a term of service")
    @API.expect(terms_of_service_model)
    @API.response(code=HTTPStatus.CREATED, model=terms_of_service_model, description="Term of service created")
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def post():
        """Create a term of service."""
        term_of_service = TermsOfServiceSchema().load(API.payload)
        created_term_of_service = TermsOfServiceModel.create_terms_of_service(term_of_service)
        return TermsOfServiceSchema().dump(created_term_of_service), HTTPStatus.CREATED
