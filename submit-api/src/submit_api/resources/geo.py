# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API blueprint for geospatial upload management.

All business logic lives in :mod:`submit_api.services.geo_processor`.
These route handlers are intentionally thin: validate → delegate → respond.
"""
import json
import logging
import time
from http import HTTPStatus

from flask import Response, current_app, request
from flask_cors import cross_origin
from flask_restx import Namespace, Resource

from submit_api.auth import auth
from submit_api.models import GeoDataUpload, db
from submit_api.services.geo_processor import GeoService
from submit_api.utils.util import allowedorigins, cors_preflight


API = Namespace("uploads", description="Endpoints for Geospatial Uploads")
logger = logging.getLogger(__name__)


@cors_preflight("GET, POST, OPTIONS")
@API.route("", methods=["GET", "POST", "OPTIONS"])
class GeoUploads(Resource):
    """Resource for managing geo uploads."""

    @staticmethod
    @cross_origin(origins=allowedorigins())
    @auth.require
    def post():
        """Create a GeoDataUpload record and kick off background processing."""
        data = request.get_json()
        try:
            upload = GeoService.create_upload(
                app=current_app._get_current_object(),  # noqa: SLF001
                filename=data.get("filename"),
                file_type=data.get("file_type"),
                file_size_kb=data.get("file_size_kb"),
                s3_key=data.get("s3_key"),
            )
        except ValueError as exc:
            return {"error": str(exc)}, HTTPStatus.BAD_REQUEST

        return {"id": upload.id, "status": upload.status}, HTTPStatus.CREATED

    @staticmethod
    @cross_origin(origins=allowedorigins())
    @auth.require
    def get():
        """Return the GeoDataUpload records for the specified item or package."""
        item_id = request.args.get("item_id", type=int)
        package_id = request.args.get("package_id", type=int)
        uploads = GeoService.list_uploads(item_id=item_id, package_id=package_id)
        return [u.to_dict() for u in uploads], HTTPStatus.OK


@cors_preflight("GET, OPTIONS")
@API.route("/<int:upload_id>/status", methods=["GET", "OPTIONS"])
class GeoUploadStatus(Resource):
    """Resource for polling geo upload status."""

    @staticmethod
    @cross_origin(origins=allowedorigins())
    @auth.require
    def get(upload_id):
        """SSE stream that polls the processing status of a single upload."""
        app = current_app._get_current_object()  # noqa: SLF001

        def generate():
            with app.app_context():
                for _ in range(60):
                    upload = db.session.get(GeoDataUpload, upload_id)
                    if not upload:
                        yield 'data: {"error": "Upload not found"}\n\n'
                        return

                    payload = {"status": upload.status, "upload_id": upload.id}

                    if upload.status == "ready":
                        payload.update({
                            "feature_count": upload.feature_count,
                            "geometry_type": upload.geometry_type,
                            "crs_original": upload.crs_original,
                            "bbox": upload.bbox,
                        })
                        yield f"data: {json.dumps(payload)}\n\n"
                        return

                    if upload.status == "failed":
                        payload["error"] = upload.error_message
                        yield f"data: {json.dumps(payload)}\n\n"
                        return

                    yield f"data: {json.dumps(payload)}\n\n"
                    time.sleep(1.5)
                    db.session.expire_all()

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )


@cors_preflight("GET, OPTIONS")
@API.route("/<int:upload_id>/url", methods=["GET", "OPTIONS"])
class GeoUploadUrl(Resource):
    """Resource for getting a presigned S3 read URL."""

    @staticmethod
    @cross_origin(origins=allowedorigins())
    @auth.require
    def get(upload_id):
        """Return a fresh presigned S3 read URL for a processed GeoDataUpload."""
        tier = request.args.get("tier", "preview")
        try:
            result = GeoService.get_presigned_read_url(upload_id, tier)
        except LookupError as exc:
            return {"error": str(exc)}, HTTPStatus.NOT_FOUND
        except ValueError as exc:
            return {"error": str(exc)}, HTTPStatus.BAD_REQUEST
        except Exception as exc:  # pylint: disable=broad-except # noqa: B902
            logger.exception("Unexpected error fetching presigned URL: %s", exc)
            return {"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR

        return result, HTTPStatus.OK


@cors_preflight("POST, OPTIONS")
@API.route("/<int:upload_id>/retry", methods=["POST", "OPTIONS"])
class GeoUploadRetry(Resource):
    """Resource for retrying an upload."""

    @staticmethod
    @cross_origin(origins=allowedorigins())
    @auth.require
    def post(upload_id):
        """Re-trigger background processing for a failed upload."""
        try:
            upload = GeoService.retry_upload(
                app=current_app._get_current_object(),  # noqa: SLF001
                upload_id=upload_id,
            )
        except LookupError as exc:
            return {"error": str(exc)}, HTTPStatus.NOT_FOUND
        except ValueError as exc:
            return {"error": str(exc)}, HTTPStatus.BAD_REQUEST

        return {"id": upload.id, "status": upload.status}, HTTPStatus.OK
