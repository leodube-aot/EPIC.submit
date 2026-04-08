"""Test Staff User API endpoints.

Tests for staff user resource endpoints.
"""

from http import HTTPStatus
from unittest.mock import patch

from faker import Faker

from submit_api.models.user import UserType
from tests.utilities.factory_scenarios import TestJwtClaims
from tests.utilities.factory_utils import (
    factory_auth_header,
    factory_user_model,
)

fake = Faker()


def test_get_staff_user_by_guid(client, session, jwt):
    """Test fetching a staff user by GUID."""
    # Create a staff user
    auth_guid = TestJwtClaims.staff_admin_role['preferred_username']
    user = factory_user_model(auth_guid=auth_guid, user_type=UserType.STAFF, session=session)

    # Create staff_user record
    from submit_api.models.staff_user import StaffUser
    staff_user_data = {
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'work_email_address': fake.email(),
        'user_id': user.id
    }
    staff_user = StaffUser.create_staff_user(staff_user_data, session=session)
    session.commit()

    # Make request
    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.get(f"/api/staff-user/{auth_guid}", headers=headers)

    assert response.status_code == HTTPStatus.OK
    data = response.get_json()
    assert data["id"] == staff_user.id
    assert data["first_name"] == staff_user_data['first_name']
    assert data["last_name"] == staff_user_data['last_name']
    assert data["work_email_address"] == staff_user_data['work_email_address']


def test_get_staff_user_not_found(client, session, jwt):
    """Test fetching a non-existent staff user."""
    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.get("/api/staff-user/non-existent-guid", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_staff_user_unauthorized(client, session):
    """Test fetching staff user without authentication."""
    response = client.get("/api/staff-user/some-guid")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_staff_user_success(client, session, jwt):
    """Test creating a staff user and assigning Keycloak role."""
    email = fake.email()
    group_name = "EAO_VIEW"

    # Mock Keycloak service responses
    mock_keycloak_user = {
        "username": f"{fake.user_name()}@idir",
        "firstName": fake.first_name(),
        "lastName": fake.last_name(),
        "email": email
    }

    with patch('submit_api.services.staff_user_service.KeycloakService.get_user_by_email') as mock_get_user, \
         patch('submit_api.services.staff_user_service.KeycloakService.get_group_id_by_path') as mock_get_group, \
         patch('submit_api.services.staff_user_service.KeycloakService.update_user_group') as mock_update_group:

        mock_get_user.return_value = mock_keycloak_user
        mock_get_group.return_value = "group-id-123"
        mock_update_group.return_value = None

        payload = {
            "email": email,
            "group_name": group_name
        }

        headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
        response = client.post("/api/staff-user/", json=payload, headers=headers)

        assert response.status_code == HTTPStatus.CREATED
        data = response.get_json()
        assert "message" in data
        assert email in data["message"]
        assert group_name in data["message"]

        # Verify Keycloak methods were called
        mock_get_user.assert_called_once_with(email)
        mock_get_group.assert_called_once_with(group_name)
        mock_update_group.assert_called_once()


def test_create_staff_user_missing_email(client, session, jwt):
    """Test creating staff user without email."""
    payload = {
        "group_name": "EAO_VIEW"
    }

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.post("/api/staff-user/", json=payload, headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.get_json()
    assert "message" in data


def test_create_staff_user_missing_group_name(client, session, jwt):
    """Test creating staff user without group name."""
    payload = {
        "email": fake.email()
    }

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.post("/api/staff-user/", json=payload, headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.get_json()
    assert "message" in data


def test_create_staff_user_keycloak_error(client, session, jwt):
    """Test creating staff user when Keycloak service fails."""
    email = fake.email()
    group_name = "EAO_VIEW"

    with patch('submit_api.services.staff_user_service.KeycloakService.get_user_by_email') as mock_get_user:
        mock_get_user.side_effect = Exception("Keycloak connection error")

        payload = {
            "email": email,
            "group_name": group_name
        }

        headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
        response = client.post("/api/staff-user/", json=payload, headers=headers)

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        data = response.get_json()
        assert "message" in data


def test_create_staff_user_unauthorized(client, session):
    """Test creating staff user without authentication."""
    payload = {
        "email": fake.email(),
        "group_name": "EAO_VIEW"
    }

    response = client.post("/api/staff-user/", json=payload)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_staff_user_without_manage_users_role(client, session, jwt):
    """Test creating staff user without MANAGE_USERS role."""
    # Use proponent role which doesn't have MANAGE_USERS permission
    payload = {
        "email": fake.email(),
        "group_name": "EAO_VIEW"
    }

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.proponent_role)
    response = client.post("/api/staff-user/", json=payload, headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_staff_user_with_existing_user(client, session, jwt):
    """Test fetching staff user when user exists with staff_user relationship."""
    auth_guid = f"{fake.user_name()}@idir"
    user = factory_user_model(auth_guid=auth_guid, user_type=UserType.STAFF, session=session)

    from submit_api.models.staff_user import StaffUser
    first_name = fake.first_name()
    last_name = fake.last_name()
    work_email = fake.email()

    staff_user_data = {
        'first_name': first_name,
        'last_name': last_name,
        'work_email_address': work_email,
        'user_id': user.id
    }
    StaffUser.create_staff_user(staff_user_data, session=session)
    session.commit()

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.get(f"/api/staff-user/{auth_guid}", headers=headers)

    assert response.status_code == HTTPStatus.OK
    data = response.get_json()
    assert data["first_name"] == first_name
    assert data["last_name"] == last_name
    assert data["work_email_address"] == work_email
    assert data["user_id"] == user.id


def test_create_staff_user_idempotent(client, session, jwt):
    """Test creating staff user multiple times is idempotent."""
    email = fake.email()
    group_name = "EAO_VIEW"
    username = f"{fake.user_name()}@idir"

    mock_keycloak_user = {
        "username": username,
        "firstName": fake.first_name(),
        "lastName": fake.last_name(),
        "email": email
    }

    with patch('submit_api.services.staff_user_service.KeycloakService.get_user_by_email') as mock_get_user, \
         patch('submit_api.services.staff_user_service.KeycloakService.get_group_id_by_path') as mock_get_group, \
         patch('submit_api.services.staff_user_service.KeycloakService.update_user_group') as mock_update_group:

        mock_get_user.return_value = mock_keycloak_user
        mock_get_group.return_value = "group-id-123"
        mock_update_group.return_value = None

        payload = {
            "email": email,
            "group_name": group_name
        }

        headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)

        # First creation
        response1 = client.post("/api/staff-user/", json=payload, headers=headers)
        assert response1.status_code == HTTPStatus.CREATED

        # Second creation - should still succeed (idempotent)
        response2 = client.post("/api/staff-user/", json=payload, headers=headers)
        assert response2.status_code == HTTPStatus.CREATED
