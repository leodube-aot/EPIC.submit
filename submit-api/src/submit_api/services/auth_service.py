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
"""Service to call epic.auth endpoints."""

import requests
from flask import current_app

from submit_api.exceptions import (
    BadRequestError,
    BusinessError,
    ResourceNotFoundError,
)
from submit_api.services.keycloak_token_service import KeycloakTokenService
from submit_api.utils.enums import HttpMethod

AUTH_APP = "SUBMIT"
API_REQUEST_TIMEOUT = 30


class AuthService:
    """Handle service requests for epic.auth."""

    @staticmethod
    def get_user_by_email(email: str):
        """Get a user by email address from epic.auth."""
        response = _request_auth_service(f"users/email/{email}")
        if response.status_code == 404:
            raise ResourceNotFoundError(
                f"User with email '{email}' not found in EPIC.auth"
            )
        return response.json()

    @staticmethod
    def get_user_by_username(username: str):
        """Get a user by username from epic.auth."""
        response = _request_auth_service(f"users/{username}")
        if response.status_code == 404:
            raise ResourceNotFoundError(
                f"User with username '{username}' not found in EPIC.auth"
            )
        return response.json()

    @staticmethod
    def get_users():
        """Get all users from epic.auth."""
        response = _request_auth_service("users", include_app_id=False)
        return response.json()

    @staticmethod
    def get_user_groups(username: str):
        """Get groups for a user by username."""
        response = _request_auth_service(f"users/{username}/groups")
        if response.status_code == 404:
            return []
        return response.json()

    @staticmethod
    def update_user_group(
        username: str, group_name: str, sub_group_name: str = None
    ):
        """Assign a user to a group by name.

        Calls PUT /api/users/<username>/groups/<group_name>.
        """
        url = f"users/{username}/groups/{group_name}"
        if sub_group_name:
            url += f"?sub_group_name={sub_group_name}"
        response = _request_auth_service(url, HttpMethod.PUT)
        if response.status_code == 404:
            raise ResourceNotFoundError(
                f"Group '{group_name}' not found in EPIC.auth"
            )
        if response.status_code not in (200, 204):
            raise BadRequestError(
                f"Failed to assign group '{group_name}' to user "
                f"'{username}'"
            )
        return response

    @staticmethod
    def delete_user_group(
        username: str,
        group_name: str,
        del_sub_group_mappings: bool = True,
    ):
        """Remove a user from a group by name.

        Calls DELETE /api/users/<username>/groups/<group_name>.
        """
        url = (
            f"users/{username}/groups/{group_name}"
            f"?del_sub_group_mappings={del_sub_group_mappings}"
        )
        response = _request_auth_service(url, HttpMethod.DELETE)
        if response.status_code == 404:
            raise ResourceNotFoundError(
                f"Group '{group_name}' not found for user '{username}'"
            )
        return response

    @staticmethod
    def delete_all_user_groups(username: str):
        """Remove all group mappings for a user.

        Calls DELETE /api/users/<username>/groups.
        """
        response = _request_auth_service(
            f"users/{username}/groups", HttpMethod.DELETE
        )
        return response.status_code == 204

    @staticmethod
    def toggle_user_enabled_status(username: str, enabled: bool):
        """Enable or disable a user's Keycloak login.

        Calls PATCH /api/users/<username> with {"enabled": enabled}.
        """
        payload = {"enabled": enabled}
        response = _request_auth_service(
            f"users/{username}", HttpMethod.PATCH, data=payload
        )
        if response.status_code == 404:
            raise ResourceNotFoundError(
                f"User '{username}' not found in EPIC.auth"
            )
        if response.status_code not in (200, 204):
            raise BadRequestError(
                f"Failed to update enabled status for user '{username}'"
            )
        return response

    @staticmethod
    def get_group_members(
        group_name: str, sub_group_name: str = None
    ):
        """Get members of a group by name.

        Calls GET /api/users/groups/<group_name>/members.
        """
        url = f"users/groups/{group_name}/members"
        if sub_group_name:
            url += f"?sub_group_name={sub_group_name}"
        response = _request_auth_service(url)
        if response.status_code == 404:
            return []
        return response.json()


def _get_token() -> str:
    """Obtain the SUBMIT service account token used to call epic.auth."""
    try:
        return KeycloakTokenService.get_service_account_token()
    except requests.exceptions.RequestException as exc:
        current_app.logger.error(
            f"Failed to obtain service account token: {str(exc)}"
        )
        raise BusinessError(
            "Unable to authenticate with the auth service", 503
        ) from exc


def _request_auth_service(
    relative_url: str,
    http_method: HttpMethod = HttpMethod.GET,
    data=None,
    include_app_id: bool = True,
):
    """Make a REST API call to epic.auth service."""
    token = _get_token()
    if not token:
        raise BusinessError("No access token found", 401)

    auth_base_url = current_app.config.get("AUTH_BASE_URL")
    if not auth_base_url:
        raise BusinessError("AUTH_BASE_URL is not configured", 500)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if include_app_id:
        headers["App-Id"] = AUTH_APP

    url = f"{auth_base_url}/api/{relative_url}"

    try:
        if http_method == HttpMethod.GET:
            response = requests.get(
                url, headers=headers, timeout=API_REQUEST_TIMEOUT
            )
        elif http_method == HttpMethod.PUT:
            response = requests.put(
                url, headers=headers, json=data, timeout=API_REQUEST_TIMEOUT
            )
        elif http_method == HttpMethod.PATCH:
            response = requests.patch(
                url, headers=headers, json=data, timeout=API_REQUEST_TIMEOUT
            )
        elif http_method == HttpMethod.DELETE:
            response = requests.delete(
                url, headers=headers, timeout=API_REQUEST_TIMEOUT
            )
        elif http_method == HttpMethod.POST:
            response = requests.post(
                url, headers=headers, json=data, timeout=API_REQUEST_TIMEOUT
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {http_method}")
    except requests.exceptions.RequestException as exc:
        current_app.logger.error(
            f"EPIC.auth service unavailable: {str(exc)}"
        )
        raise BusinessError(
            "The auth service is temporarily unavailable", 503
        ) from exc

    return response
