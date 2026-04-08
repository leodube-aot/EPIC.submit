"""Test submission item note creation."""

from http import HTTPStatus

from faker import Faker

from tests.utilities.factory_scenarios import TestJwtClaims
from tests.utilities.factory_utils import factory_auth_header, factory_item_model, factory_user_model


fake = Faker()


def test_create_note_success(client, session, jwt):
    """Test creating a staff note for a submission item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]

    factory_user_model(auth_guid=auth_guid)
    item = factory_item_model(item_type_id=1, status="NEW", submitted_by=auth_guid)

    session.flush()

    headers = factory_auth_header(jwt=jwt, claims=claims)

    payload = {
        "note": fake.text(max_nb_chars=1000)
    }

    response = client.post(
        f"/api/notes/submission-items/{item.id}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.get_json()

    assert data["note"] == payload["note"]
    assert data["item_id"] == item.id
