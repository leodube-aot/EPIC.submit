"""Test for staff package."""
from http import HTTPStatus

from tests.utilities.factory_scenarios import TestPackageScenarios
from tests.utilities.factory_utils import setup_authenticated_proponent


class TestStaffPackageVersions:
    """Test staff package versions endpoint."""

    def test_get_package_versions_as_staff(self, client, session, jwt):
        """Test GET /api/packages/{id}/versions returns versions for a staff user."""
        # Step 1: Create package as proponent
        headers, account_project = setup_authenticated_proponent(session, jwt)
        payload = TestPackageScenarios.get_payload()

        response = client.post(
            f"/api/packages/account-projects/{account_project.id}",
            json=payload,
            headers=headers,
        )
        assert response.status_code == HTTPStatus.CREATED
        created_package = response.json
        original_package_id = created_package["id"]

        # Step 3: Call the staff versions endpoint
        response = client.get(
            f"/api/packages/{original_package_id}/versions",
            headers=headers,
        )
        assert response.status_code == HTTPStatus.OK

        versions = response.json
        assert isinstance(versions, list)
        assert len(versions) >= 1

        version = versions[0]
        assert version["original_package_id"] == original_package_id
        assert "id" in version
        assert "package_id" in version
        assert "version" in version
        assert isinstance(version["version"], int)
