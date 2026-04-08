# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS',
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API endpoints for retrieving activity logs."""

from http import HTTPStatus

from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import jwt
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.activity_log import ActivityLogSchema
from submit_api.services.activity_log_service import ActivityLogService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("activity-logs", description="Endpoints for Activity Log Management")

activity_log_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, ActivityLogSchema(many=True), "ActivityLogs"
)


@cors_preflight("GET, OPTIONS")
@API.route(
    "/<string:entity_type>/<int:entity_id>",
    methods=["GET", "OPTIONS"],
)
class ActivityLog(Resource):
    """Resource for retrieving activity logs."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get activity logs for a specific entity.")
    @API.response(
        code=HTTPStatus.OK, model=activity_log_model, description="Activity Logs"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @API.response(HTTPStatus.NOT_FOUND, "Not Found")
    @cross_origin(origins=allowedorigins())
    def get(entity_type, entity_id):
        """Retrieve activity logs for a specific entity type and ID."""
        # Retrieve logs
        is_staff = jwt.contains_role([EpicSubmitRole.EAO_VIEW.value])
        logs = ActivityLogService.get_activity_logs(entity_type, entity_id)
        schema = ActivityLogSchema(many=True, context={"is_proponent": not is_staff})
        return schema.dump(logs), HTTPStatus.OK
