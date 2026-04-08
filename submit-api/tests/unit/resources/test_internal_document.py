"""Test Internal Staff Document API endpoints.

Tests for internal staff document resource endpoints.
"""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from faker import Faker

from tests.utilities.factory_scenarios import TestJwtClaims
from tests.utilities.factory_utils import (
    factory_auth_header,
    factory_package_model,
    factory_user_model,
    setup_authenticated_proponent,
)

fake = Faker()

INTERNAL_DOCS_BASE_URL = "/api/internal-staff-documents/packages"


# ---------------------------------------------------------------------------
# POST – create internal staff document
# ---------------------------------------------------------------------------

def test_create_internal_document_success(client, session, jwt):
    """Test successfully creating an internal staff document."""
    auth_guid = TestJwtClaims.staff_admin_role["preferred_username"]
    factory_user_model(auth_guid=auth_guid)

    _, account_project = setup_authenticated_proponent(session, jwt)
    package = factory_package_model(account_project=account_project)

    payload = {
        "name": fake.file_name(extension="pdf"),
        "url": fake.url(),
        "type": "LINK",
    }

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.post(
        f"{INTERNAL_DOCS_BASE_URL}/{package.id}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.get_json()
    assert data["name"] == payload["name"]
    assert data["url"] == payload["url"]
    assert data["package_id"] == package.id


def test_create_internal_document_package_not_found(client, session, jwt):
    """Test creating a document for a non-existent package returns 404."""
    auth_guid = TestJwtClaims.staff_admin_role["preferred_username"]
    factory_user_model(auth_guid=auth_guid)

    payload = {
        "name": fake.file_name(extension="pdf"),
        "url": fake.url(),
        "type": "LINK",
    }

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.post(
        f"{INTERNAL_DOCS_BASE_URL}/99999",
        json=payload,
        headers=headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_create_internal_document_unauthorized(client, session, jwt):
    """Test creating a document without authentication returns 401."""
    _, account_project = setup_authenticated_proponent(session, jwt)
    package = factory_package_model(account_project=account_project)

    payload = {
        "name": fake.file_name(extension="pdf"),
        "url": fake.url(),
        "type": "LINK",
    }

    response = client.post(
        f"{INTERNAL_DOCS_BASE_URL}/{package.id}",
        json=payload,
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


# ---------------------------------------------------------------------------
# DELETE – delete internal staff document
# ---------------------------------------------------------------------------

def test_delete_internal_document_success(client, session, jwt):
    """Test successfully deleting an internal staff document."""
    auth_guid = TestJwtClaims.staff_admin_role["preferred_username"]
    factory_user_model(auth_guid=auth_guid)

    _, account_project = setup_authenticated_proponent(session, jwt)
    package = factory_package_model(account_project=account_project)

    # Create a document first so there is something to delete
    create_payload = {
        "name": fake.file_name(extension="pdf"),
        "url": fake.url(),
        "type": "LINK",
    }
    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    create_response = client.post(
        f"{INTERNAL_DOCS_BASE_URL}/{package.id}",
        json=create_payload,
        headers=headers,
    )
    assert create_response.status_code == HTTPStatus.CREATED
    document_id = create_response.get_json()["id"]

    delete_response = client.delete(
        f"{INTERNAL_DOCS_BASE_URL}/{document_id}",
        headers=headers,
    )

    assert delete_response.status_code == HTTPStatus.OK
    data = delete_response.get_json()
    assert data["id"] == document_id


def test_delete_internal_document_not_found(client, session, jwt):
    """Test deleting a non-existent internal staff document returns 404."""
    auth_guid = TestJwtClaims.staff_admin_role["preferred_username"]
    factory_user_model(auth_guid=auth_guid)

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.delete(
        f"{INTERNAL_DOCS_BASE_URL}/99999",
        headers=headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_internal_document_unauthorized(client, session):
    """Test deleting a document without authentication returns 401."""
    response = client.delete(f"{INTERNAL_DOCS_BASE_URL}/1")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


# ---------------------------------------------------------------------------
# Response schema validation
# ---------------------------------------------------------------------------

def test_create_internal_document_response_schema(client, session, jwt):
    """Test that the creation response contains all expected schema fields."""
    auth_guid = TestJwtClaims.staff_admin_role["preferred_username"]
    factory_user_model(auth_guid=auth_guid)

    _, account_project = setup_authenticated_proponent(session, jwt)
    package = factory_package_model(account_project=account_project)

    payload = {
        "name": fake.file_name(extension="docx"),
        "url": fake.url(),
        "type": "LINK",
    }

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.post(
        f"{INTERNAL_DOCS_BASE_URL}/{package.id}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.get_json()

    # Verify all expected top-level fields are present
    for field in ("id", "name", "url", "package_id"):
        assert field in data, f"Expected field '{field}' missing from response"


def test_delete_internal_document_response_schema(client, session, jwt):
    """Test that the deletion response contains all expected schema fields."""
    auth_guid = TestJwtClaims.staff_admin_role["preferred_username"]
    factory_user_model(auth_guid=auth_guid)

    _, account_project = setup_authenticated_proponent(session, jwt)
    package = factory_package_model(account_project=account_project)

    # Create then immediately delete
    create_payload = {
        "name": fake.file_name(extension="docx"),
        "url": fake.url(),
        "type": "LINK",
    }
    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)

    create_resp = client.post(
        f"{INTERNAL_DOCS_BASE_URL}/{package.id}",
        json=create_payload,
        headers=headers,
    )
    document_id = create_resp.get_json()["id"]

    delete_resp = client.delete(
        f"{INTERNAL_DOCS_BASE_URL}/{document_id}",
        headers=headers,
    )

    assert delete_resp.status_code == HTTPStatus.OK
    data = delete_resp.get_json()
    for field in ("id", "name", "url", "package_id"):
        assert field in data, f"Expected field '{field}' missing from delete response"