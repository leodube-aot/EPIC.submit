"""Test Project.

Test for project.
"""
import copy
from http import HTTPStatus

from faker import Faker

from submit_api import get_named_config
from tests.utilities.factory_scenarios import TestJwtClaims
from tests.utilities.factory_utils import (
    factory_account_model, factory_account_project_model, factory_auth_header, setup_authenticated_proponent,
    factory_project_model, factory_proponent_model, factory_user_model)

fake = Faker()


CONFIG = get_named_config("testing")

PROJECTS_URL = "/api/projects"


def test_get_project_by_id(client, session, jwt):
    """Test get project by id"""
    auth_guid = TestJwtClaims.staff_admin_role['preferred_username']
    factory_user_model(auth_guid=auth_guid)

    proponent_name = "Test Proponent Name"
    proponent_id = fake.random_int(min=1000, max=9999)
    factory_proponent_model(id=proponent_id, name=proponent_name, is_deleted=False)

    account = factory_account_model(proponent_id=proponent_id)
    project = factory_project_model(name="TestProject", proponent_id=proponent_id)
    account_project = factory_account_project_model(account_id=account.id, project_id=project.id)

    session.flush()

    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)

    response = client.get(
        f"{PROJECTS_URL}/{account_project.id}",
        headers=headers
    )

    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    assert data["id"] == account_project.id
    assert data["project"]["name"] == "TestProject"

    assert "proponent" in data["project"]
    assert data["project"]["proponent"] is not None
    assert data["project"]["proponent"]["name"] == proponent_name


def test_get_project_by_id_no_roles(client, session, jwt):
    """Test project access with valid JWT but no roles."""
    claims = copy.deepcopy(TestJwtClaims.staff_admin_role.value)
    claims["realm_access"]["roles"] = []
    claims["resource_access"][CONFIG.JWT_OIDC_TEST_AUDIENCE]["roles"] = []

    auth_guid = claims['preferred_username']
    factory_user_model(auth_guid=auth_guid)

    account = factory_account_model()
    project = factory_project_model(name="TestProjectNoRoles", proponent_id=111222)
    account_project = factory_account_project_model(account_id=account.id, project_id=project.id)

    session.flush()
    headers = factory_auth_header(jwt=jwt, claims=claims)

    response = client.get(f"{PROJECTS_URL}/{account_project.id}", headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_project_by_id_invalid_jwt(client):
    """Test project access with invalid JWT token."""
    invalid_token = "Bearer this.is.not.valid"

    response = client.get(
        f"{PROJECTS_URL}/1",
        headers={"Authorization": invalid_token}
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_projects_by_account(client, session, jwt):
    """Returns projects for the given account."""
    headers, account_project = setup_authenticated_proponent(session, jwt)

    response = client.get(
        f"{PROJECTS_URL}/accounts/{account_project.account_id}",
        headers=headers,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.get_json()
    assert isinstance(data, list)
    assert any(p["id"] == account_project.id for p in data)


def test_get_projects_by_account_unauthorized(client, session):
    """Missing auth header returns 401."""
    response = client.get(f"{PROJECTS_URL}/accounts/1")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_bulk_add_projects(client, session, jwt):
    """Staff can bulk-add projects to an account."""
    auth_guid = TestJwtClaims.staff_admin_role["preferred_username"]
    factory_user_model(auth_guid=auth_guid)

    account = factory_account_model()
    project1 = factory_project_model(name="Bulk Project 1")
    project2 = factory_project_model(name="Bulk Project 2")

    payload = {"project_ids": [project1.id, project2.id]}
    headers = factory_auth_header(jwt=jwt, claims=TestJwtClaims.staff_admin_role)
    response = client.post(
        f"{PROJECTS_URL}/accounts/{account.id}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.get_json()
    assert isinstance(data, list)
    project_ids_in_response = [p["id"] for p in data]
    assert project1.id in project_ids_in_response
    assert project2.id in project_ids_in_response


def test_bulk_add_projects_unauthorized(client, session):
    """Missing auth header returns 401."""
    payload = {"project_ids": [1, 2]}
    response = client.post(
        f"{PROJECTS_URL}/accounts/1", json=payload
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_projects_by_proponent(client, session):
    """Returns a list of projects for the given proponent."""
    proponent = factory_proponent_model(id=fake.random_int(1000, 9999), name="Test Corp")
    project1 = factory_project_model(name="ProponentProj A", proponent_id=proponent.id)
    project2 = factory_project_model(name="ProponentProj B", proponent_id=proponent.id)

    response = client.get(f"{PROJECTS_URL}/proponents/{proponent.id}")

    assert response.status_code == HTTPStatus.OK
    data = response.get_json()
    assert isinstance(data, list)
    ids = [p["id"] for p in data]
    assert project1.id in ids
    assert project2.id in ids


def test_get_projects_by_user(client, session, jwt):
    """Returns projects associated with the given user."""
    headers, account_project = setup_authenticated_proponent(session, jwt)

    from submit_api.models import AccountUser
    account_user = AccountUser.query.filter_by(
        account_id=account_project.account_id
    ).first()

    response = client.get(
        f"{PROJECTS_URL}/users/{account_user.user_id}", headers=headers
    )

    assert response.status_code == HTTPStatus.OK
    data = response.get_json()
    assert isinstance(data, list)


def test_get_projects_by_user_unauthorized(client, session):
    """Missing auth header returns 401."""
    response = client.get(f"{PROJECTS_URL}/users/1")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
