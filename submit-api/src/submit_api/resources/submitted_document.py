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
"""API endpoints for managing a document resource."""

from http import HTTPStatus

from flask import request
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.models.account_project_search_options import DocumentSearchOptions
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.submission import SubmissionSchema, SubmittedDocumentByProjectSchema
from submit_api.services.submitted_document_service import DocumentService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("documents", description="Endpoints for Submitted Document Management")
"""Custom exception messages
"""

document_list_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SubmittedDocumentByProjectSchema(), "Document"
)


@cors_preflight("GET, OPTIONS")
@API.route(
    "",
    methods=["GET", "OPTIONS"],
)
class AccountDocuments(Resource):
    """Resource for managing submitted documents."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get submitted documents")
    @API.response(
        code=HTTPStatus.OK, model=document_list_model, description="Get documents"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_VIEW.value])
    @cross_origin(origins=allowedorigins())
    def get():
        """Get all submitted documents."""
        args = request.args
        search_text = args.get('search_text')
        search_options = DocumentSearchOptions(
            search_text=search_text,
        )

        documents = DocumentService.get_all_documents(search_options)
        return SubmittedDocumentByProjectSchema(many=True).dump(documents), HTTPStatus.OK


@cors_preflight("GET, OPTIONS")
@API.route(
    "/failed/items/<int:item_id>",
    methods=["GET", "OPTIONS"],
)
class ItemFailedDocuments(Resource):
    """Resource for managing submitted documents."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get submitted documents")
    @API.response(
        code=HTTPStatus.OK, model=document_list_model, description="Get documents"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_VIEW.value])
    @cross_origin(origins=allowedorigins())
    def get(item_id):
        """Get all failed documents by item id."""
        documents = DocumentService.get_failed_documents_by_item_id(item_id)
        return SubmissionSchema(many=True).dump(documents), HTTPStatus.OK


@cors_preflight("GET, OPTIONS")
@API.route(
    "/submissions/packages/<int:package_id>",
    methods=["GET", "OPTIONS"],
)
class SubmittedDocuments(Resource):
    """Resource for managing submitted documents."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get submitted documents")
    @API.response(
        code=HTTPStatus.OK, model=document_list_model, description="Get documents"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_VIEW.value])
    @cross_origin(origins=allowedorigins())
    def get(package_id):
        """Get all submitted documents by package id."""
        documents = DocumentService.get_submissions_by_package_id(package_id)
        return SubmissionSchema(many=True).dump(documents), HTTPStatus.OK
