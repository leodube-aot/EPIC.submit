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
"""API endpoints for managing a internal staff document resource."""

from http import HTTPStatus

from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.internal_staff_document import InternalStaffDocumentSchema, PostInternalStaffDocument
from submit_api.services.internal_staff_document_service import InternalStaffDocumentService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("internal-staff-documents", description="Endpoints for Internal Staff Document Management")
"""Custom exception messages
"""

create_internal_document = ApiHelper.convert_ma_schema_to_restx_model(
    API, PostInternalStaffDocument(), "Create an internal staff document"
)
internal_document = ApiHelper.convert_ma_schema_to_restx_model(
    API, InternalStaffDocumentSchema(), "Internal Staff Document"
)


@cors_preflight("OPTIONS, POST, DELETE")
@API.route("/packages/<int:package_id>", methods=["POST", "OPTIONS", "DELETE"])
class InternalStaffDocuments(Resource):
    """Resource for managing projects."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Create an internal staff document")
    @API.expect(create_internal_document)
    @API.response(
        code=HTTPStatus.CREATED, model=internal_document, description="Created Internal Staff Document"
    )
    @API.response(HTTPStatus.NOT_FOUND, "Not found")
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_CREATE.value])
    @cross_origin(origins=allowedorigins())
    def post(package_id):
        """Create an internal staff document."""
        create_document_data = PostInternalStaffDocument().load(API.payload)
        created_document = (InternalStaffDocumentService
                            .create_internal_staff_document(package_id, create_document_data))
        return InternalStaffDocumentSchema().dump(created_document), HTTPStatus.CREATED

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Delete an internal staff document")
    @API.response(
        code=HTTPStatus.OK, model=internal_document, description="Deleted Internal Staff Document"
    )
    @API.response(HTTPStatus.NOT_FOUND, "Not found")
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_CREATE.value])
    @cross_origin(origins=allowedorigins())
    def delete(package_id):
        """Delete an internal staff document."""
        deleted_document = (InternalStaffDocumentService
                            .delete_internal_staff_document(package_id))
        return InternalStaffDocumentSchema().dump(deleted_document), HTTPStatus.OK
