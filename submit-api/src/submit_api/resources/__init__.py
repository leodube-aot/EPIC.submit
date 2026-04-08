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
"""Exposes all of the resource endpoints mounted in Flask-Blueprint style.

Uses restplus namespaces to mount individual api endpoints into the service.

All services have 2 defaults sets of endpoints:
 - ops
 - meta
That are used to expose operational health information about the service, and meta information.
"""

from flask import Blueprint

from .account import API as ACCOUNT_API
from .account_terms_of_service import API as ACCOUNT_TERMS_OF_SERVICE_API
from .account_user import API as ACCOUNT_USER_API
from .activity_log import API as ACTIVITY_LOG_API
from .apihelper import Api
from .geo import API as GEO_UPLOAD_API
from .internal_document import API as INTERNAL_DOCUMENT_API
from .invitation import API as INVITATION_API
from .item import API as ITEM_API
from .migration_ops import API as MIGRATION_API
from .ops import API as OPS_API
from .package import API as PACKAGE_API
from .package_type import API as PACKAGE_TYPE_API
from .project import API as PROJECT_API
from .proponent import API as PROPONENT_API
from .staff_user import API as STAFF_USER_API
from .submission import API as SUBMISSION_API
from .submission_item_note import API as SUBMISSION_ITEM_NOTE_API
from .submitted_document import API as SUBMITTED_DOCUMENT_API
from .user import API as USER_API


__all__ = ('API_BLUEPRINT', 'OPS_BLUEPRINT', 'STAFF_API_BLUEPRINT', 'GEO_API_BLUEPRINT')

URL_PREFIX = '/api'
API_BLUEPRINT = Blueprint('API', __name__, url_prefix=f"{URL_PREFIX}/")
OPS_BLUEPRINT = Blueprint("API_OPS", __name__, url_prefix="/ops")
STAFF_API_BLUEPRINT = Blueprint("STAFF_API", __name__, url_prefix=f"{URL_PREFIX}/staff")
GEO_API_BLUEPRINT = Blueprint("GEO_API", __name__, url_prefix=f"{URL_PREFIX}/geo")

API_OPS = Api(
    OPS_BLUEPRINT,
    title="Service OPS API",
    version="1.0",
    description="The Core API for the Reports System",
)

API_OPS.add_namespace(OPS_API, path="/")
API_OPS.add_namespace(MIGRATION_API, path="/")

API = Api(
    API_BLUEPRINT,
    title='SUBMIT API',
    version='1.0',
    description='The Core API for SUBMIT'
)

# HANDLER = ExceptionHandler(API)

API.add_namespace(ACCOUNT_API)
API.add_namespace(USER_API)
API.add_namespace(PROJECT_API)
API.add_namespace(PACKAGE_API)
API.add_namespace(ITEM_API)
API.add_namespace(SUBMISSION_API)
API.add_namespace(INVITATION_API)
API.add_namespace(ACCOUNT_USER_API)
API.add_namespace(ACTIVITY_LOG_API)
API.add_namespace(ACCOUNT_TERMS_OF_SERVICE_API)
API.add_namespace(PROPONENT_API)
API.add_namespace(INTERNAL_DOCUMENT_API)
API.add_namespace(SUBMITTED_DOCUMENT_API)
API.add_namespace(SUBMISSION_ITEM_NOTE_API)
API.add_namespace(STAFF_USER_API)

STAFF_API = Api(
    STAFF_API_BLUEPRINT,
    title='STAFF SUBMIT API',
    version='1.0',
    description='The Core API for staff of SUBMIT'
)

STAFF_API.add_namespace(PACKAGE_TYPE_API)

GEO_API = Api(
    GEO_API_BLUEPRINT,
    title='GEO SUBMIT API',
    version='1.0',
    description='The Core API for Geospatial Uploads'
)

GEO_API.add_namespace(GEO_UPLOAD_API, path="/uploads")
