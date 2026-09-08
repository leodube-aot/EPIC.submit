"""Service for submission management."""
from typing import Protocol

from flask import current_app

from submit_api.exceptions import BadRequestError, ResourceNotFoundError
from submit_api.models import Item as ItemModel
from submit_api.models import Package as PackageModel
from submit_api.models import SubmittedDocument as SubmittedDocumentModel
from submit_api.models.db import session_scope
from submit_api.models.package_version import PackageVersion as PackageVersionModel
from submit_api.models.submission import Submission as SubmissionModel, SubmissionStatus
from submit_api.models.submission import SubmissionType
from submit_api.models.submitted_form import SubmittedForm as SubmittedFormModel
from submit_api.utils.token_info import TokenInfo


def _find_previous_version_item(item_id):
    """Find the matching item on the previous package version.

    Returns the previous item if this is a revision package (version 2+)
    and a matching item exists on the prior version, otherwise None.
    """
    item = ItemModel.find_by_id(item_id)
    if not item:
        return None

    package = PackageModel.find_by_id(item.package_id)
    if not package or not package.version:
        return None

    # Only relevant if this is version 2+
    if package.version.version <= 1:
        return None

    # Find the previous version's package
    previous_version = PackageVersionModel.query.filter_by(
        original_package_id=package.version.original_package_id,
        version=package.version.version - 1
    ).first()

    if not previous_version or not previous_version.package:
        return None

    # Find matching item by type_id on the previous package
    return ItemModel.query.filter_by(
        package_id=previous_version.package.id,
        type_id=item.type_id
    ).first()


class SubmissionCreatorFactory(Protocol):
    """Submission creator factory protocol."""

    def create(self, item_id, request_data, session=None) -> SubmissionModel:
        """Create a new submission."""
        return SubmissionModel()

    def replace(self, submission_id, request_data) -> SubmissionModel:
        """Replace a submission."""
        raise BadRequestError("Replace not supported for this submission type.")

    def move(self, submission_id, request_data) -> SubmissionModel:
        """Move a submission."""
        raise BadRequestError("Move not supported for this submission type.")

    def soft_delete(self, submission_id) -> SubmissionModel:
        """Soft delete a submission."""
        raise BadRequestError("Soft delete not supported for this submission type.")


class FormSubmissionCreator(SubmissionCreatorFactory):
    """Form submission creator."""

    def create(self, item_id, request_data, _session=None):
        """Create a new form submission."""
        current_app.logger.info("Creating form submission for item_id: %s.", item_id)
        if _session:
            submission = self._create(item_id, request_data, _session)
        else:
            with session_scope() as session:
                submission = self._create(item_id, request_data, session)
        current_app.logger.info("Successfully created form submission with id: %s.", submission.id)
        return submission

    def _create(self, item_id, request_data, session):
        """Create a new form submission."""
        submitted_form = self._create_submitted_form(session, request_data)
        submission = self._create_submission(session, item_id, submitted_form.id)
        return submission

    @staticmethod
    def _create_submitted_form(session, request_data):
        """Create a new submitted form."""
        current_app.logger.debug("Creating new SubmittedFormModel.")
        submitted_form = SubmittedFormModel(
            submission_json=request_data
        )
        session.add(submitted_form)
        session.commit()
        session.flush()
        current_app.logger.debug("Successfully created SubmittedFormModel with id: %s.", submitted_form.id)
        return submitted_form

    @staticmethod
    def _create_submission(session, item_id, submitted_form_id):
        """Create a new submission."""
        current_app.logger.debug("Creating new SubmissionModel for form.")
        previous_submission = SubmissionModel.find_latest_by_type_and_item_id(
            item_id, SubmissionType.FORM.value)
        if previous_submission:
            current_app.logger.error("Form submission for item_id: %s already exists.", item_id)
            raise ValueError("Form submission already created.")

        submission = SubmissionModel(
            item_id=item_id,
            type=SubmissionType.FORM.value,
            submitted_form_id=submitted_form_id,
            created_by=TokenInfo.get_username()
        )
        session.add(submission)
        session.commit()
        session.flush()
        current_app.logger.debug("Successfully created SubmissionModel for form with id: %s.", submission.id)
        return submission


class DocumentSubmissionCreator(SubmissionCreatorFactory):
    """Document submission creator."""

    def create(self, item_id, request_data, _session=None):
        """Create a new document submission."""
        current_app.logger.info("Creating document submission for item_id: %s.", item_id)
        if _session:
            submission = self._create(item_id, request_data, _session)
        else:
            with session_scope() as session:
                submission = self._create(item_id, request_data, session)
        current_app.logger.info("Successfully created document submission with id: %s.", submission.id)
        return submission

    def _create(self, item_id, request_data, session):
        """Create a new document submission."""
        submitted_document = self._create_submitted_document(session, request_data)
        root_submission_id = self._resolve_root_submission_id_from_previous_version(
            item_id, submitted_document.folder, submitted_document.name
        )
        submission_data = {
            "item_id": item_id,
            "submitted_document_id": submitted_document.id,
        }
        if root_submission_id:
            submission_data["root_submission_id"] = root_submission_id
        submission: SubmissionModel = self._create_submission(session, submission_data)

        return submission

    def replace(self, submission_id, request_data):
        """Replace a document submission."""
        current_app.logger.info("Replacing document submission_id: %s.", submission_id)
        with session_scope() as session:
            submission: SubmissionModel = SubmissionModel.find_by_id(
                submission_id)
            if not submission:
                current_app.logger.error("Submission with id %s not found for replacement.", submission_id)
                raise ResourceNotFoundError(f"Submission with ID {submission_id} not found.")

            status = submission.status
            allowed_statuses = [SubmissionStatus.SUBMITTED,
                                SubmissionStatus.REJECTED,
                                SubmissionStatus.PENDING,
                                SubmissionStatus.VERIFIED,
                                SubmissionStatus.ACKNOWLEDGED]
            if status not in allowed_statuses:
                current_app.logger.warning(
                    "Attempted to replace a document with non-replaceable status '%s' for submission_id: %s.",
                    status, submission_id
                )
                raise BadRequestError(f"Cannot replace a document with status {status}.")

            request_data['folder'] = submission.submitted_document.folder
            submitted_document = self._create_submitted_document(session, request_data)
            new_submission = self._create_submission(
                session,
                {
                    "item_id": submission.item_id,
                    "submitted_document_id": submitted_document.id,
                    "original_submission_id": submission.id,
                    "root_submission_id": submission.root_submission_id,
                    "status": SubmissionStatus.PENDING,
                    "created_by": TokenInfo.get_username()
                }
            )
            current_app.logger.info("New submission created with id: %s to replace submission_id: %s.",
                                    new_submission.id, submission_id)

            if submission.status == SubmissionStatus.PENDING:
                current_app.logger.info("Marking submission_id: %s as deleted and inactive.", submission_id)
                submission.deleted = True
                submission.active = False
                session.add(submission)

            return new_submission

    @staticmethod
    def _validate_status_allowed(submission):
        """Ensure the submission is in a state that allows movement."""
        allowed_statuses = [
            SubmissionStatus.SUBMITTED,
            SubmissionStatus.REJECTED,
        ]

        if submission.status not in allowed_statuses:
            current_app.logger.warning(
                "Move validation failed for submission_id: %s due to status: %s.",
                submission.id, submission.status
            )
            raise BadRequestError(f"Cannot move a document with status {submission.status}.")

    @staticmethod
    def _validate_not_same_submission(submission, target_submission):
        if submission.id == target_submission.id:
            current_app.logger.warning(
                "Move validation failed: attempt to replace submission %s with itself.", submission.id
            )
            raise BadRequestError("Cannot replace a submission with itself.")

    @staticmethod
    def _validate_submission_is_active(submission):
        if not (submission.active and not submission.deleted):
            current_app.logger.warning(
                "Move validation failed: submission %s is not active.", submission.id
            )
            raise BadRequestError("Cannot replace a submission that is not active.")

    @staticmethod
    def _validate_same_package(submission, target_submission):
        submission_item = ItemModel.find_by_id(submission.item_id)
        target_submission_item = ItemModel.find_by_id(target_submission.item_id)
        if submission_item.package_id != target_submission_item.package_id:
            current_app.logger.warning(
                "Move validation failed: submission %s and target %s are in different packages.",
                submission.id, target_submission.id
            )
            raise BadRequestError("Cannot replace a submission in a different package.")

    def _validate_move_request(self, submission, target_submission=None):
        """Run all validations before creating a new version of the target submission."""
        current_app.logger.debug("Validating move request for submission_id: %s.", submission.id)
        self._validate_status_allowed(submission)
        self._validate_submission_is_active(submission)

        if target_submission:
            self._validate_not_same_submission(submission, target_submission)
            self._validate_submission_is_active(target_submission)
            self._validate_same_package(submission, target_submission)
        current_app.logger.debug("Move request validation successful for submission_id: %s.", submission.id)

    @staticmethod
    def _fill_missing_name(request_data, submission):
        """Find the document name if not in the request."""
        if not request_data.get('name'):
            current_app.logger.debug("Document name missing, attempting to find from previous document.")
            previous_doc = SubmittedDocumentModel.find_by_id(submission.submitted_document_id)
            if previous_doc:
                request_data['name'] = previous_doc.name
                current_app.logger.debug("Found document name: %s.", previous_doc.name)

    def _create_next_version_of_target(self, session, submission, request_data):
        """Replace an existing target submission with a new version."""
        target_submission_id = request_data.get("target_submission_id")
        current_app.logger.info("Creating next version of target submission %s from source submission %s.",
                                target_submission_id, submission.id)
        target_submission: SubmissionModel = SubmissionModel.find_by_id(target_submission_id)

        if not target_submission:
            current_app.logger.error("Target submission with ID %s not found.", target_submission_id)
            raise ResourceNotFoundError(f"Target submission with ID {target_submission_id} not found.")

        self._validate_move_request(submission, target_submission)

        self._fill_missing_name(request_data, submission)
        request_data['folder'] = target_submission.submitted_document.folder
        submitted_document = self._create_submitted_document(session, request_data)
        new_submission = self._create_submission(
            session,
            {
                "item_id": target_submission.item_id,
                "submitted_document_id": submitted_document.id,
                "original_submission_id": target_submission.id,
                "root_submission_id": target_submission.root_submission_id,
                "status": submission.status,
                "created_by": submission.created_by
            }
        )
        current_app.logger.info("Created new version submission with id: %s.", new_submission.id)

        current_app.logger.info("Deactivating target submission_id: %s.", target_submission.id)
        target_submission.active = False
        session.add(target_submission)

        current_app.logger.info("Deactivating and deleting source submission_id: %s.", submission.id)
        submission.active = False
        submission.deleted = True
        session.add(submission)

        return new_submission

    @staticmethod
    def _restore_previous_active_submission(session, moved_submission):
        """Restore the most recent previous version if none are currently active."""
        current_app.logger.info("Checking if restore is needed for submissions related to root_submission_id: %s.",
                                moved_submission.root_submission_id)
        active_exists = session.query(SubmissionModel).filter(
            SubmissionModel.root_submission_id == moved_submission.root_submission_id,
            SubmissionModel.id != moved_submission.id,
            SubmissionModel.deleted.is_(False),
            SubmissionModel.active.is_(True)
        ).first()

        if active_exists:
            current_app.logger.info("Active submission %s already exists. No restore needed.", active_exists.id)
            return

        current_app.logger.info("No active submission found. Attempting to restore previous version.")
        previous_version = (
            session.query(SubmissionModel)
            .filter(
                SubmissionModel.item_id == moved_submission.item_id,
                SubmissionModel.root_submission_id == moved_submission.root_submission_id,
                SubmissionModel.id != moved_submission.id,
                SubmissionModel.deleted.is_(False),
                SubmissionModel.active.is_(False),
                SubmissionModel.minor_version == moved_submission.minor_version - 1
            )
            .first()
        )

        if previous_version and not previous_version.active:
            current_app.logger.info("Restoring previous submission_id: %s by setting active=True.", previous_version.id)
            previous_version.active = True
            session.add(previous_version)
        else:
            current_app.logger.info("No previous version found or it is already active. Nothing to restore.")

        return

    def _move_to_folder(self, session, submission, request_data):
        """Move document to a specific folder."""
        self._validate_move_request(submission)
        current_app.logger.info("Moving document submission %s to folder %s.",
                                submission.id, request_data.get('destination_folder'))

        destination_item_id = request_data.get('destination_item_id')
        destination_url = request_data.get('destination_url')

        submitted_document = SubmittedDocumentModel.find_by_id(submission.submitted_document_id)
        if destination_url == submitted_document.url and submission.minor_version == 1:
            current_app.logger.info("Destination URL is the same. No move needed for submission_id: %s.", submission.id)
            return submission

        self._fill_missing_name(request_data, submission)

        request_data['folder'] = request_data.get('destination_folder')
        new_submitted_document = self._create_submitted_document(session, request_data)

        new_submission = self._create_submission(
            session,
            {
                "item_id": destination_item_id,
                "submitted_document_id": new_submitted_document.id,
                "status": submission.status,
                "created_by": submission.created_by
            }
        )
        current_app.logger.info("Created new submission with id: %s for the move operation.", new_submission.id)
        current_app.logger.info("Deactivating and deleting original submission_id: %s.", submission.id)
        submission.active = False
        submission.deleted = True

        session.add(submission)

        return new_submission

    def move(self, submission_id, request_data):
        """Move a document submission."""
        current_app.logger.info("Starting move operation for submission_id: %s.", submission_id)
        with session_scope() as session:
            submission: SubmissionModel = SubmissionModel.find_by_id(submission_id)
            if not submission:
                current_app.logger.error("Submission with id %s not found for move operation.", submission_id)
                raise ResourceNotFoundError(f"Submission with ID {submission_id} not found.")

            if request_data.get("target_submission_id"):
                current_app.logger.info("Move operation is a 'create next version' for submission_id: %s.",
                                        submission_id)
                moved_submission = self._create_next_version_of_target(session, submission, request_data)
            else:
                current_app.logger.info("Move operation is a 'move to folder' for submission_id: %s.", submission_id)
                moved_submission = self._move_to_folder(session, submission, request_data)

            self._restore_previous_active_submission(session, submission)
            current_app.logger.info("Move operation completed for submission_id: %s. New submission is %s.",
                                    submission_id, moved_submission.id)
            return moved_submission

    @staticmethod
    def _find_previous_version_item(item_id):
        """Find the matching item on the previous package version.

        Returns the previous item if this is a revision package (version 2+)
        and a matching item exists on the prior version, otherwise None.
        """
        item = ItemModel.find_by_id(item_id)
        if not item:
            return None

        package = PackageModel.find_by_id(item.package_id)
        if not package or not package.version:
            return None

        # Only relevant if this is version 2+
        if package.version.version <= 1:
            return None

        # Find the previous version's package
        previous_version = PackageVersionModel.query.filter_by(
            original_package_id=package.version.original_package_id,
            version=package.version.version - 1
        ).first()

        if not previous_version or not previous_version.package:
            return None

        # Find matching item by type_id on the previous package
        return ItemModel.query.filter_by(
            package_id=previous_version.package.id,
            type_id=item.type_id
        ).first()

    @staticmethod
    def _resolve_root_submission_id_from_previous_version(item_id, folder=None, name=None):
        """Look up root_submission_id from the previous package version's matching item.

        When a document is uploaded to a revision package (version 2+), this finds
        the corresponding submission on the previous package version (matched by item
        type_id and document folder) and returns its root_submission_id so the new
        submission continues the same version lineage.

        When multiple previous submissions share the same folder, the match is
        disambiguated first by document name, then by falling back to the latest
        version's lineage. Since all versions of a document within a package share
        the same root_submission_id, choosing the latest is sufficient to continue
        the correct lineage.
        """
        previous_item = DocumentSubmissionCreator._find_previous_version_item(
            item_id
        )
        if not previous_item:
            return None

        # Find active document submissions on the previous item
        previous_submissions = (
            SubmissionModel.query
            .filter_by(
                item_id=previous_item.id,
                type=SubmissionType.DOCUMENT,
                deleted=False
            )
            .filter(SubmissionModel.status != SubmissionStatus.PENDING)
            .order_by(
                SubmissionModel.major_version.desc(),
                SubmissionModel.minor_version.desc()
            )
            .all()
        )

        if not previous_submissions:
            return None

        # If a folder is provided, narrow to submissions in the same folder.
        if folder:
            folder_matches = [
                s for s in previous_submissions
                if s.submitted_document
                and s.submitted_document.folder == folder
            ]
            if folder_matches:
                return DocumentSubmissionCreator._pick_root_submission_id(
                    folder_matches, name, previous_item.id
                )

        # No folder provided or no folder matches — resolve against all submissions.
        return DocumentSubmissionCreator._pick_root_submission_id(
            previous_submissions, name, previous_item.id
        )

    @staticmethod
    def _pick_root_submission_id(candidates, name, previous_item_id):
        """Pick the root_submission_id from candidate previous submissions.

        Candidates are expected to be ordered by version descending. When a name is
        provided and uniquely matches a candidate, that candidate's lineage is used.
        Otherwise the latest version's root_submission_id is returned so the lineage
        is continued rather than dropped.
        """
        if not candidates:
            return None

        # Prefer a unique match by document name (the same document re-uploaded).
        if name:
            name_matches = [
                s for s in candidates
                if s.submitted_document and s.submitted_document.name == name
            ]
            if len(name_matches) == 1:
                return name_matches[0].root_submission_id

        # Fall back to the latest version's lineage. All versions of a document
        # within a package share the same root_submission_id, so taking the latest
        # continues the correct lineage instead of self-rooting a new one.
        distinct_roots = {
            s.root_submission_id for s in candidates if s.root_submission_id
        }
        if len(distinct_roots) > 1:
            current_app.logger.debug(
                "Multiple distinct document lineages found on item %s. "
                "Using the latest version's lineage.",
                previous_item_id
            )
        return candidates[0].root_submission_id

    @classmethod
    def get_document_version(cls, item_id, original_submission_id=None):
        """Get the latest document version."""
        current_app.logger.debug("Getting document version for item_id: %s.", item_id)
        submission_item = ItemModel.find_by_id(item_id)
        submission_package = PackageModel.find_by_id(submission_item.package_id)
        package_version = submission_package.version
        major_version = package_version.version if package_version else 1

        if not original_submission_id or not submission_package.submitted_on:
            minor_version = 1
            current_app.logger.debug("No original submission or package not submitted. Version: %s.%s.",
                                     major_version, minor_version)
            return major_version, minor_version

        original_submission = SubmissionModel.find_by_id(original_submission_id)
        if original_submission.status == SubmissionStatus.PENDING:
            minor_version = original_submission.minor_version
            current_app.logger.debug("Original submission is PENDING. Using its minor version. Version: %s.%s.",
                                     major_version, minor_version)
            return major_version, minor_version

        minor_version = original_submission.minor_version + 1
        current_app.logger.debug("Incrementing minor version. Version: %s.%s.", major_version, minor_version)
        return major_version, minor_version

    @staticmethod
    def _create_submitted_document(session, request_data):
        """Create a new submitted document."""
        url = request_data.get('url') or request_data.get('destination_url')
        folder = request_data.get('folder')

        if not folder:
            current_app.logger.error("Folder is required for document submission but was not provided.")
            raise BadRequestError("Folder is required for document submission.")
        current_app.logger.debug("Creating submitted document with URL: %s and folder: %s", url, folder)
        submitted_document = SubmittedDocumentModel(
            name=request_data.get('name'),
            url=url,
            folder=folder
        )
        session.add(submitted_document)
        session.flush()
        current_app.logger.debug("Successfully created SubmittedDocumentModel with id: %s.", submitted_document.id)
        return submitted_document

    @staticmethod
    def _create_submission(session, submission_data):
        """Create a new submission."""
        current_app.logger.debug("Creating new SubmissionModel for document.")
        major_version, minor_version = DocumentSubmissionCreator.get_document_version(
            submission_data.get("item_id"), submission_data.get("original_submission_id")
        )
        submission = SubmissionModel(
            item_id=submission_data.get("item_id"),
            type=submission_data.get("type", SubmissionType.DOCUMENT),
            submitted_document_id=submission_data.get("submitted_document_id"),
            major_version=major_version,
            minor_version=minor_version,
            created_by=submission_data.get("created_by", TokenInfo.get_username()),
            root_submission_id=submission_data.get("root_submission_id"),
            status=submission_data.get("status", SubmissionStatus.PENDING)
        )
        session.add(submission)
        session.flush()
        current_app.logger.debug("Created SubmissionModel with id: %s, version %s.%s.",
                                 submission.id, major_version, minor_version)

        if submission.root_submission_id is None:
            submission.root_submission_id = submission.id
            current_app.logger.debug("Setting root_submission_id to self: %s.", submission.id)
            session.flush()

        return submission

    def soft_delete(self, submission_id) -> SubmissionModel:
        """Soft delete a submission."""
        current_app.logger.info("Soft deleting submission_id: %s.", submission_id)
        with session_scope() as session:
            submission: SubmissionModel = SubmissionModel.find_by_id(submission_id)
            if not submission:
                current_app.logger.error("Submission with id %s not found for soft delete.", submission_id)
                raise ResourceNotFoundError(f"Submission with ID {submission_id} not found.")

            submission.deleted = True
            submission.active = False
            session.add(submission)
            self._restore_previous_active_submission(session, submission)
            current_app.logger.info("Successfully soft deleted submission_id: %s.", submission.id)
            return submission
