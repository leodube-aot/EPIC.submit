"""Package Type resource for staff users."""
from http import HTTPStatus

from flask import request
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.package_type_create import PackageTypeCreateSchema
from submit_api.schemas.package_type_response import PackageTypeResponseSchema
from submit_api.services.package_type_service import PackageTypeService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import cors_preflight


API = Namespace('package-types', description='Package Type Management')

"""Custom exception messages
"""

package_type_create_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, PackageTypeCreateSchema(), "PackageTypeCreate"
)

package_type_response_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, PackageTypeResponseSchema(), "PackageTypeResponse"
)


@cors_preflight('POST,OPTIONS')
@API.route('', methods=['POST', 'OPTIONS'])
class PackageTypeResource(Resource):
    """Resource for creating/updating package types."""

    @API.doc('create_package_type')
    @API.expect(package_type_create_model)
    @API.response(
        code=HTTPStatus.OK,
        model=package_type_response_model,
        description='Package type created/updated successfully'
    )
    @API.response(HTTPStatus.BAD_REQUEST, 'Validation error')
    @API.response(HTTPStatus.NOT_FOUND, 'Phase or item types not found')
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_CREATE.value])
    def post(self):
        """Create or update a package type with phase association.

        This endpoint is idempotent - it will create a new package type if it doesn't exist,
        or update the existing one if it does. It also supports creating new item types on the fly.

        The phase is identified by:
        - EA Act name (e.g., "EA Act (2018)")
        - Work Type name (e.g., "Assessment", "Amendment")
        - Phase name (e.g., "Early Engagement", "EAC Application Review")

        Item types can be specified in two ways:
        1. By ID for existing item types: {"id": 1}
        2. By name and submission_method for new item types:
           {"name": "Custom Document", "submission_method": "DOCUMENT_UPLOAD"}
        """
        # Validate request data
        schema = PackageTypeCreateSchema()
        data = schema.load(request.get_json())

        # Create or update package type
        result = PackageTypeService.create_or_update_package_type(
            ea_act_name=data['ea_act_name'],
            work_type_name=data['work_type_name'],
            phase_name=data['phase_name'],
            package_type_name=data['package_type_name'],
            item_types=data['item_types']
        )

        return result, HTTPStatus.OK
