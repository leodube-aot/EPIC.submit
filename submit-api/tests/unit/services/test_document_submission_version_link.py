"""Unit tests for cross-package root_submission_id linking in DocumentSubmissionCreator."""
from unittest.mock import Mock, patch

import pytest

from submit_api.services.submission import submission_creator_factory as factory_module
from submit_api.models.submission import SubmissionStatus, SubmissionType
from submit_api.services.submission.submission_creator_factory import DocumentSubmissionCreator


MODULE_PATH = "submit_api.services.submission.submission_creator_factory"


@pytest.fixture(autouse=True)
def mock_current_app():
    """Patch current_app to avoid application context errors."""
    with patch.object(factory_module, "current_app", new=Mock()):
        yield


@pytest.fixture()
def mock_item():
    """Create a mock item."""
    item = Mock()
    item.id = 10
    item.package_id = 100
    item.type_id = 5
    return item


@pytest.fixture()
def mock_package_version_2():
    """Create a mock package that is version 2."""
    package = Mock()
    package.id = 100
    package.version = Mock()
    package.version.version = 2
    package.version.original_package_id = 50
    return package


@pytest.fixture()
def mock_package_version_1():
    """Create a mock package that is version 1."""
    package = Mock()
    package.id = 80
    package.version = Mock()
    package.version.version = 1
    package.version.original_package_id = 50
    return package


@pytest.fixture()
def mock_previous_item():
    """Create a mock item from the previous package version."""
    item = Mock()
    item.id = 8
    item.package_id = 80
    item.type_id = 5
    return item


@pytest.fixture()
def mock_previous_submission():
    """Create a mock submission from the previous package version."""
    submission = Mock()
    submission.id = 110
    submission.root_submission_id = 110
    submission.major_version = 1
    submission.minor_version = 2
    submission.type = SubmissionType.DOCUMENT
    submission.status = SubmissionStatus.SUBMITTED
    submission.active = True
    submission.deleted = False
    submission.submitted_document = Mock()
    submission.submitted_document.folder = "management_plans"
    return submission


class TestResolveRootSubmissionIdFromPreviousVersion:
    """Tests for _resolve_root_submission_id_from_previous_version."""

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_links_root_submission_id_on_version_2_package(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item, mock_previous_submission
    ):
        """Version 2+ package correctly links to previous version's root_submission_id."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        # PackageVersion query for previous version
        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        # Item query for previous package's matching item
        mock_item_model.query.filter_by.return_value.first.return_value = mock_previous_item

        # Submission query for previous item's submissions
        mock_sub_model.query.filter_by.return_value.filter.return_value \
            .order_by.return_value.all.return_value = [mock_previous_submission]

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans"
        )

        assert result == 110

    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    @patch(f"{MODULE_PATH}.ItemModel")
    def test_returns_none_for_version_1_package(
        self, mock_item_model, mock_find_package,
        mock_item, mock_package_version_1
    ):
        """Version 1 package should not attempt to link (returns None)."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_1

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans"
        )

        assert result is None

    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    @patch(f"{MODULE_PATH}.ItemModel")
    def test_returns_none_when_package_has_no_version(
        self, mock_item_model, mock_find_package, mock_item
    ):
        """Package without a version record should not link."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_package = Mock()
        mock_package.version = None
        mock_find_package.return_value = mock_package

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans"
        )

        assert result is None

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_returns_none_when_no_previous_submissions(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item
    ):
        """No previous document submissions means no linkage."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        mock_item_model.query.filter_by.return_value.first.return_value = mock_previous_item

        mock_sub_model.query.filter_by.return_value.filter.return_value \
            .order_by.return_value.all.return_value = []

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans"
        )

        assert result is None

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_links_latest_lineage_when_multiple_same_folder_and_same_root(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item
    ):
        """Multiple versions of one document (same root) in a folder link to that root."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        mock_item_model.query.filter_by.return_value.first.return_value = mock_previous_item

        # Two versions (1.2 and 1.1) of the SAME document lineage — same root.
        # Ordered by version desc, so the latest (1.2) is first.
        sub_v2 = Mock()
        sub_v2.root_submission_id = 110
        sub_v2.submitted_document = Mock()
        sub_v2.submitted_document.folder = "management_plans"
        sub_v2.submitted_document.name = "plan.pdf"

        sub_v1 = Mock()
        sub_v1.root_submission_id = 110
        sub_v1.submitted_document = Mock()
        sub_v1.submitted_document.folder = "management_plans"
        sub_v1.submitted_document.name = "plan.pdf"

        mock_sub_model.query.filter_by.return_value.filter.return_value \
            .order_by.return_value.all.return_value = [sub_v2, sub_v1]

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans"
        )

        # Should inherit the shared lineage rather than self-rooting a new one.
        assert result == 110

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_disambiguates_by_document_name_when_multiple_lineages_in_folder(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item
    ):
        """When multiple distinct lineages share a folder, match by document name."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        mock_item_model.query.filter_by.return_value.first.return_value = mock_previous_item

        sub_a = Mock()
        sub_a.root_submission_id = 110
        sub_a.submitted_document = Mock()
        sub_a.submitted_document.folder = "management_plans"
        sub_a.submitted_document.name = "plan-a.pdf"

        sub_b = Mock()
        sub_b.root_submission_id = 112
        sub_b.submitted_document = Mock()
        sub_b.submitted_document.folder = "management_plans"
        sub_b.submitted_document.name = "plan-b.pdf"

        mock_sub_model.query.filter_by.return_value.filter.return_value \
            .order_by.return_value.all.return_value = [sub_a, sub_b]

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans", name="plan-b.pdf"
        )

        # Name uniquely identifies the second lineage.
        assert result == 112

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_falls_back_to_latest_when_name_does_not_match(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item
    ):
        """When name does not uniquely match, fall back to the latest lineage."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        mock_item_model.query.filter_by.return_value.first.return_value = mock_previous_item

        # Latest first (ordered desc).
        sub_latest = Mock()
        sub_latest.root_submission_id = 200
        sub_latest.submitted_document = Mock()
        sub_latest.submitted_document.folder = "management_plans"
        sub_latest.submitted_document.name = "plan-old.pdf"

        sub_older = Mock()
        sub_older.root_submission_id = 201
        sub_older.submitted_document = Mock()
        sub_older.submitted_document.folder = "management_plans"
        sub_older.submitted_document.name = "plan-older.pdf"

        mock_sub_model.query.filter_by.return_value.filter.return_value \
            .order_by.return_value.all.return_value = [sub_latest, sub_older]

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans", name="brand-new-name.pdf"
        )

        # No name match → latest version's lineage.
        assert result == 200

    @patch(f"{MODULE_PATH}.ItemModel")
    def test_returns_none_when_item_not_found(self, mock_item_model):
        """Non-existent item returns None."""
        mock_item_model.find_by_id.return_value = None

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=999, folder="management_plans"
        )

        assert result is None

    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_returns_none_when_no_matching_item_on_previous_package(
        self, mock_find_package, mock_pv_model, mock_item_model,
        mock_item, mock_package_version_2
    ):
        """No matching item by type_id on previous package returns None."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        mock_item_model.query.filter_by.return_value.first.return_value = None

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans"
        )

        assert result is None

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_links_single_submission_without_folder_match(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item, mock_previous_submission
    ):
        """Single previous submission links even if folder doesn't match (fallback)."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        mock_item_model.query.filter_by.return_value.first.return_value = mock_previous_item

        # Previous submission is in a different folder
        mock_previous_submission.submitted_document.folder = "consultation_records"

        mock_sub_model.query.filter_by.return_value.filter.return_value \
            .order_by.return_value.all.return_value = [mock_previous_submission]

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="management_plans"
        )

        # Falls through folder matching (no match), but single submission links
        assert result == 110


class TestSupportingDocumentReuploadOnRevisionPackage:
    """Simulate re-uploading one of several supporting documents on a revision (v2+) package.

    A single item can hold multiple supporting-document lineages within the same folder.
    When the proponent re-uploads one of them on a revision package, the new submission
    must continue the correct lineage (matched by document name) rather than merging into
    another document's lineage or self-rooting a brand-new one.
    """

    @staticmethod
    def _wire_previous_version(
        mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item, previous_submissions
    ):
        """Wire up the mocks so the previous package version resolves to the given submissions."""
        mock_item_model.find_by_id.return_value = mock_item
        mock_find_package.return_value = mock_package_version_2

        mock_prev_version = Mock()
        mock_prev_version.package = Mock()
        mock_prev_version.package.id = 80
        mock_pv_model.query.filter_by.return_value.first.return_value = mock_prev_version

        mock_item_model.query.filter_by.return_value.first.return_value = mock_previous_item

        mock_sub_model.query.filter_by.return_value.filter.return_value \
            .order_by.return_value.all.return_value = previous_submissions

    @staticmethod
    def _make_supporting_doc(root_submission_id, name, folder="supporting_documents"):
        """Build a mock supporting-document submission."""
        submission = Mock()
        submission.root_submission_id = root_submission_id
        submission.submitted_document = Mock()
        submission.submitted_document.folder = folder
        submission.submitted_document.name = name
        return submission

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_reupload_links_to_matching_supporting_document_lineage(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item
    ):
        """Re-uploading a named supporting doc links to that document's lineage, not the latest."""
        # Three distinct supporting documents in the same folder on the previous version.
        # Ordered by version desc, so the "latest" (appendix-c) is first.
        appendix_c = self._make_supporting_doc(303, "appendix-c.pdf")
        appendix_b = self._make_supporting_doc(302, "appendix-b.pdf")
        appendix_a = self._make_supporting_doc(301, "appendix-a.pdf")
        previous = [appendix_c, appendix_b, appendix_a]

        self._wire_previous_version(
            mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
            mock_item, mock_package_version_2, mock_previous_item, previous
        )

        # Proponent re-uploads "appendix-b.pdf" (NOT the latest document).
        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="supporting_documents", name="appendix-b.pdf"
        )

        # Must continue appendix-b's lineage, not appendix-c's (the latest).
        assert result == 302

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_brand_new_supporting_document_falls_back_to_latest(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item
    ):
        """Uploading a brand-new supporting doc name falls back to the latest lineage.

        This documents the known limitation: a genuinely new supporting document on a
        revision package cannot be distinguished from a rename, so it attaches to the
        latest existing lineage rather than self-rooting.
        """
        appendix_b = self._make_supporting_doc(302, "appendix-b.pdf")
        appendix_a = self._make_supporting_doc(301, "appendix-a.pdf")
        previous = [appendix_b, appendix_a]

        self._wire_previous_version(
            mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
            mock_item, mock_package_version_2, mock_previous_item, previous
        )

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="supporting_documents", name="appendix-d-new.pdf"
        )

        # No name match → latest lineage (appendix-b).
        assert result == 302

    @patch(f"{MODULE_PATH}.SubmissionModel")
    @patch(f"{MODULE_PATH}.ItemModel")
    @patch(f"{MODULE_PATH}.PackageVersionModel")
    @patch(f"{MODULE_PATH}.PackageModel.find_by_id")
    def test_reupload_ignores_documents_in_other_folders(
        self, mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
        mock_item, mock_package_version_2, mock_previous_item
    ):
        """A same-named document in a different folder is not used for linkage."""
        supporting_doc = self._make_supporting_doc(
            401, "shared-name.pdf", folder="supporting_documents"
        )
        other_folder_doc = self._make_supporting_doc(
            402, "shared-name.pdf", folder="management_plans"
        )
        previous = [other_folder_doc, supporting_doc]

        self._wire_previous_version(
            mock_find_package, mock_pv_model, mock_item_model, mock_sub_model,
            mock_item, mock_package_version_2, mock_previous_item, previous
        )

        result = DocumentSubmissionCreator._resolve_root_submission_id_from_previous_version(
            item_id=10, folder="supporting_documents", name="shared-name.pdf"
        )

        # Only the supporting_documents-folder doc is a candidate.
        assert result == 401
