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
"""API endpoints for managing a project resource."""

from http import HTTPStatus

from flask import abort, request
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.models.account_project_search_options import AccountProjectSearchOptions
from submit_api.models.package import NonCanonicalPackageStatus, PackageStatus
from submit_api.resources.apihelper import Api as ApiHelper
from submit_api.schemas.project import AddProjectSchema, ProjectSchema, StaffAccountProjectSchema
from submit_api.services.project_service import ProjectService
from submit_api.utils.roles import EpicSubmitRole
from submit_api.utils.util import allowedorigins, cors_preflight


DEFAULT_PAGE_SIZE = 3
DEFAULT_PAGE = 1

API = Namespace("projects", description="Endpoints for Project Management")
"""Custom exception messages
"""

project_add_list = ApiHelper.convert_ma_schema_to_restx_model(
    API, AddProjectSchema(), "Project Add"
)
project_list_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, ProjectSchema(), "Project"
)
staff_project_list_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, StaffAccountProjectSchema(), "Project"
)


@cors_preflight("GET, OPTIONS")
@API.route("", methods=["GET", "OPTIONS"])
class AccountProjects(Resource):
    """Resource for managing account projects with pagination."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get paginated projects")
    @API.response(
        code=HTTPStatus.OK, model=project_list_model, description="Get paginated projects"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_VIEW.value])
    @cross_origin(origins=allowedorigins())
    def get():
        """Get paginated account projects."""
        args = request.args
        search_text = args.get('search_text')
        submitted_on_start = args.get('submitted_on_start')
        submitted_on_end = args.get('submitted_on_end')
        raw_statuses = args.getlist("status[]")
        status = []
        for _status in raw_statuses:
            result = PackageStatus.check_value(_status) or NonCanonicalPackageStatus.check_value(_status)
            if result:
                status.append(result)
            else:
                abort(400, f"Unknown status: {_status}")
        page = int(args.get('page', DEFAULT_PAGE))  # Default to page 1
        page_size = int(args.get('page_size', DEFAULT_PAGE_SIZE))  # Default to 10 items per page

        search_options = AccountProjectSearchOptions(
            search_text=search_text,
            submitted_on_start=submitted_on_start,
            submitted_on_end=submitted_on_end,
            status=status,
        )

        # Fetch paginated projects
        account_projects, total_projects = ProjectService.get_all_account_projects_paginated(
            search_options, page, page_size, is_proponent=False
        )

        # Calculate next cursor (if applicable)
        next_cursor = page + 1 if page * page_size < total_projects else None

        return {
            "projects": account_projects,
            "next_cursor": next_cursor,
            "total": total_projects,
        }, HTTPStatus.OK


@cors_preflight("GET, OPTIONS, POST")
@API.route(
    "/<int:account_project_id>",
    methods=["POST", "GET", "OPTIONS"],
)
class AccountProject(Resource):
    """Resource for managing projects."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get project by project_id")
    @API.response(
        code=HTTPStatus.CREATED, model=project_list_model, description="Get project"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.has_one_of_staff_roles([EpicSubmitRole.EAO_VIEW.value])
    def get(account_project_id):
        """Get project by id."""
        account_project = ProjectService.get_account_project_by_id(account_project_id, is_staff=True)
        if not account_project:
            return {"message": "Account project not found"}, HTTPStatus.NOT_FOUND
        return account_project, HTTPStatus.OK


@cors_preflight("GET, OPTIONS, POST")
@API.route("/accounts/<int:account_id>", methods=["POST", "GET", "OPTIONS"])
class ProjectsByAccount(Resource):
    """Resource for managing projects."""

    @staticmethod
    @ApiHelper.swagger_decorators(
        API, endpoint_description="Get projects by account id"
    )
    @API.response(
        code=HTTPStatus.OK, model=project_list_model, description="Get projects"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(account_id):
        """Get projects by account id."""
        args = request.args
        search_text = args.get('search_text')
        submitted_on_start = args.get('submitted_on_start')
        submitted_on_end = args.get('submitted_on_end')
        raw_statuses = args.getlist("status[]")
        status = []
        for _status in raw_statuses:
            result = PackageStatus.check_value(_status) or NonCanonicalPackageStatus.check_value(_status)
            if result:
                status.append(result)
            else:
                abort(400, f"Unknown status: {_status}")
        search_options = AccountProjectSearchOptions(
            search_text=search_text,
            submitted_on_start=submitted_on_start,
            submitted_on_end=submitted_on_end,
            status=status,
        )
        projects = ProjectService.get_projects_by_account_id(account_id, search_options)
        return projects, HTTPStatus.OK

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Add projects in bulk")
    @API.expect(project_add_list)
    @API.response(
        code=HTTPStatus.CREATED, model=project_list_model, description="Added projects"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def post(account_id):
        """Add projects in bulk."""
        projects_data = AddProjectSchema().load(API.payload)
        added_projects = ProjectService.bulk_add_projects(
            account_id, projects_data.get("project_ids")
        )
        return ProjectSchema(many=True).dump(added_projects), HTTPStatus.CREATED


@cors_preflight("GET, OPTIONS, POST")
@API.route("/proponents/<int:proponent_id>", methods=["POST", "GET", "OPTIONS"])
class Project(Resource):
    """Resource for managing projects."""

    @staticmethod
    @ApiHelper.swagger_decorators(
        API, endpoint_description="Get projects by proponent id"
    )
    @API.response(
        code=HTTPStatus.OK, model=project_list_model, description="Get project"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    def get(proponent_id):
        """Get projects by proponent id."""
        projects = ProjectService.get_projects_by_proponent_id(proponent_id)
        return ProjectSchema(many=True).dump(projects), HTTPStatus.OK


@cors_preflight("GET, OPTIONS, POST")
@API.route(
    "/<int:account_project_id>",
    methods=["POST", "GET", "OPTIONS"],
)
class Projects(Resource):
    """Resource for managing projects."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get project by project_id")
    @API.response(
        code=HTTPStatus.CREATED, model=project_list_model, description="Get project"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @cross_origin(origins=allowedorigins())
    @auth.require
    def get(account_project_id):
        """Get account project by account_project_id."""
        account_project = ProjectService.get_account_project_by_id(account_project_id, is_staff=False)
        if not account_project:
            return {"message": "Account project not found"}, HTTPStatus.NOT_FOUND
        return account_project, HTTPStatus.OK


@cors_preflight("GET, OPTIONS, POST")
@API.route("/users/<int:user_id>", methods=["POST", "GET", "OPTIONS"])
class ProjectsByAccountUser(Resource):
    """Resource for managing projects."""

    @staticmethod
    @ApiHelper.swagger_decorators(
        API, endpoint_description="Get projects by account id"
    )
    @API.response(
        code=HTTPStatus.OK, model=project_list_model, description="Get projects"
    )
    @API.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @auth.require
    @cross_origin(origins=allowedorigins())
    def get(user_id):
        """Get projects by user id."""
        projects = ProjectService.get_account_projects_by_user_id(user_id)
        return projects, HTTPStatus.OK
