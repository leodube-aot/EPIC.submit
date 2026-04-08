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
"""API endpoints for managing a submission resource."""

from http import HTTPStatus

from flask import current_app, jsonify
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.submission import CreateSubmissionRequestSchema, SubmissionSchema
from submit_api.services.submission import SubmissionService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("submissions", description="Endpoints for Submission Management")
"""Custom exception messages
"""

create_submission_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, CreateSubmissionRequestSchema(), "Create a submission"
)
submission_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SubmissionSchema(), "Submission"
)


@cors_preflight("GET, OPTIONS, POST")
@API.route("/items/<int:submission_item_id>", methods=["POST", "GET", "OPTIONS"])
class SubmissionByItem(Resource):
    """Resource for managing submissions."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Create a submission")
    @API.expect(create_submission_model)
    @API.response(
        code=HTTPStatus.CREATED, model=submission_model, description="Submission"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def post(submission_item_id):
        """Create a submission."""
        create_submission_data = CreateSubmissionRequestSchema().load(API.payload)
        created_submission = SubmissionService.create_submission(submission_item_id, create_submission_data)
        return SubmissionSchema().dump(created_submission), HTTPStatus.CREATED


@cors_preflight("GET, OPTIONS, PATCH")
@API.route("/<int:submission_id>/form", methods=["PATCH", "GET", "OPTIONS"])
class Submissions(Resource):
    """Resource for managing submissions."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Edit a submission")
    @API.expect(create_submission_model)
    @API.response(
        code=HTTPStatus.OK, model=submission_model, description="Submission"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def patch(submission_id):
        """Edit a submission."""
        edit_submission_data = CreateSubmissionRequestSchema().load(API.payload)
        edited_submission = SubmissionService.edit_submission_form(submission_id, edit_submission_data)
        return SubmissionSchema().dump(edited_submission), HTTPStatus.OK


@cors_preflight("GET, OPTIONS")
@API.route("/<int:submission_id>/versions", methods=["GET", "OPTIONS"])
class SubmissionVersions(Resource):
    """Resource for retrieving all versions of a submission."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get all versions of a submission")
    @API.response(
        code=HTTPStatus.OK,
        model=[submission_model],
        description="List of submission versions"
    )
    @API.response(HTTPStatus.NOT_FOUND, "Submission not found")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def get(submission_id):
        """Fetch all versions of a submission based on its root submission ID."""
        submissions = SubmissionService.get_all_versions(submission_id)
        return SubmissionSchema(many=True).dump(submissions), HTTPStatus.OK


@cors_preflight("OPTIONS, POST, DELETE")
@API.route("/<int:submission_id>/document", methods=["POST", "OPTIONS", "DELETE"])
class DocumentSubmission(Resource):
    """Resource for managing a document submission."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Replace a document submission")
    @API.expect(create_submission_model)
    @API.response(
        code=HTTPStatus.OK, model=submission_model, description="Submission"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def post(submission_id):
        """Replace a submission document."""
        new_submission_data = CreateSubmissionRequestSchema().load(API.payload)
        created_submission = SubmissionService.replace_submission(submission_id, new_submission_data)
        return SubmissionSchema().dump(created_submission), HTTPStatus.CREATED

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Delete a document submission")
    @API.expect(create_submission_model)
    @API.response(
        code=HTTPStatus.OK, model=submission_model, description="Submission"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def delete(submission_id):
        """Delete a submission document."""
        deleted_submission = SubmissionService.delete_submission(submission_id)
        return SubmissionSchema().dump(deleted_submission), HTTPStatus.OK


@cors_preflight("OPTIONS, DELETE")
@API.route("/<int:submission_id>/document/soft-delete", methods=["OPTIONS", "DELETE"])
class DocumentSubmissionSoftDelete(Resource):
    """Resource for managing a document submission."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Soft delete a document submission")
    @API.response(
        code=HTTPStatus.OK, model=submission_model, description="Submission"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_EDIT.value])
    def delete(submission_id):
        """Soft delete a submission document."""
        deleted_submission = SubmissionService.soft_delete_submission(submission_id)
        return SubmissionSchema().dump(deleted_submission), HTTPStatus.OK


@cors_preflight("OPTIONS, POST")
@API.route("/<int:submission_id>/document/move", methods=["POST", "OPTIONS"])
class DocumentSubmissionMove(Resource):
    """Resource to move a document submission."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Move a document submission")
    @API.expect(create_submission_model)
    @API.response(
        code=HTTPStatus.OK, model=submission_model, description="Submission moved"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def post(submission_id):
        """Move a submission document."""
        move_submission_data = CreateSubmissionRequestSchema().load(API.payload)
        created_submission = SubmissionService.move_submission(submission_id, move_submission_data)
        return SubmissionSchema().dump(created_submission), HTTPStatus.CREATED


@cors_preflight("OPTIONS, POST")
@API.route("/items/<int:submission_item_id>/geo-process", methods=["POST", "OPTIONS"])
class SubmissionItemGeoProcess(Resource):
    """Resource to trigger geospatial processing for a submission item."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Trigger geospatial processing")
    @API.response(HTTPStatus.ACCEPTED, "Processing triggered")
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def post(submission_item_id):
        """Trigger geospatial processing for newly uploaded files."""
        try:
            triggered_uploads = SubmissionService.trigger_geo_process(submission_item_id)
            return jsonify({
                'message': f'Triggered {len(triggered_uploads)} geo-processes',
                'uploads': triggered_uploads
            }), HTTPStatus.ACCEPTED
        except Exception as e:  # noqa: B902
            current_app.logger.exception(f"Error triggering geo process: {e}")
            return jsonify({'error': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
