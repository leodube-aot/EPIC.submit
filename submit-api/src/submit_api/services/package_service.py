"""Service for package management."""
# pylint: disable=too-many-lines
from collections import defaultdict
from datetime import datetime, UTC

from flask import current_app
from sqlalchemy import func

from submit_api.enums.activity_type import ActorTypeEnum, ActivityActionType
from submit_api.enums.item_status import ItemStatus
from submit_api.enums.package_type import (
    MANAGEMENT_PLAN_RELATED_TYPES,
    PackageApprovalType,
    PackageTypeEnum,
)
from submit_api.enums.role import ProponentPermissionsEnum
from submit_api.exceptions import BadRequestError, ResourceNotFoundError
from submit_api.models import Item as ItemModel, Submission, User
from submit_api.models import Package as PackageModel
from submit_api.models import PackageType as PackageTypeModel
from submit_api.models import PackageVersion as PackageVersionModel
from submit_api.models import UpdateRequest as UpdateRequestModel
from submit_api.models.account_project_work import AccountProjectWork as AccountProjectWorkModel
from submit_api.models.db import session_scope
from submit_api.models.package import PackageStatus, NonCanonicalPackageStatus
from submit_api.models.package_item_type import PackageItemType as PackageItemTypeModel
from submit_api.models.package_metadata import PackageMetadata as PackageMetadataModel
from submit_api.models.package_metadata import PackageMetadataFields
from submit_api.models.queries.package import PackageItemQueries
from submit_api.models.queries.package import PackageSubmissionQueries
from submit_api.models.submission import SubmissionType, SubmissionStatus
from submit_api.models.item_type import SubmissionItemType, SubmissionMethod
from submit_api.models.submission_review import SubmissionReviewStatus
from submit_api.models.update_request import UpdateRequestType, UpdateRequestStatus
from submit_api.models.user import UserType
from submit_api.services import authorization
from submit_api.services.authorization import has_gis_extended_edit_role
from submit_api.services.activity_log_service import ActivityLogService
from submit_api.services.geo import GeoService
from submit_api.services.email_queue_service import SubmitEmailQueueService
from submit_api.utils.constants import (
    GIS_ITEM_TYPE_NAME,
    MANAGEMENT_PLAN_RESUBMISSION_REQUEST_EMAIL_TEMPLATE,
    MANAGEMENT_PLAN_UPDATE_REQUEST_CREATED_EMAIL_TEMPLATE,
    SUBMISSION_ACKNOWLEDGED_CONFIRMATION_EMAIL_TEMPLATE,
    SUBMISSION_WITHDRAWN_CONFIRMATION_EMAIL_TEMPLATE,
)
from submit_api.utils.token_info import TokenInfo
from submit_api.services.package_version_service import PackageVersionService

# Canonical chip display order (D9).
# Primary status first, then review stream, then overlays last.
# Rule: Passed Consultation Check must never sort before Under Consultation Check.
CANONICAL_STATUS_ORDER = (
    # Primary / base statuses
    'NEW', 'CREATED', 'IN_PROGRESS', 'SUBMITTED', 'NEW_SUBMISSION', 'RESUBMITTED',
    # Terminal outcomes
    'APPROVED', 'ACCEPTED', 'SATISFIED', 'REVIEWED', 'NO_REVISION_REQUIRED',
    'VERIFIED', 'ACKNOWLEDGED', 'NOT_APPROVED', 'REVIEW_REJECTED', 'WITHDRAWN',
    # Review stream statuses
    'UNDER_CONSULTATION_CHECK', 'PASSED_CONSULTATION_CHECK',
    'UNDER_REVIEW', 'AWAITING_MANAGER_APPROVAL',
    # Acknowledgement stream
    'INTERNAL_VERIFICATION', 'PENDING_ACKNOWLEDGEMENT',
    'READY_FOR_ACKNOWLEDGEMENT', 'READY_FOR_APPROVAL',
    # Overlays (always last)
    'UPDATE_REQUESTED', 'REVISION_REQUIRED', 'REVISION_REQUESTED', 'UPDATED',
)


class PackageService:
    """Package management service."""

    @staticmethod
    def _get_status_mapping(version):
        """Get the package status mapping dictionary."""
        return {
            # work related package statuses
            PackageStatus.NEW.value: {
                UserType.PROPONENT: PackageStatus.NEW.value,
                # Version 1 is a brand-new package: EAO sees "Created".
                # A later version is created via the "+ Create New" button on an
                # already-approved package, so the EAO should see "New" as well.
                UserType.STAFF: (PackageStatus.CREATED.value if version == 1
                                 else PackageStatus.NEW.value)
            },
            PackageStatus.IN_PROGRESS.value: {
                UserType.PROPONENT: PackageStatus.IN_PROGRESS.value,
                UserType.STAFF: PackageStatus.CREATED.value
            },
            PackageStatus.SUBMITTED.value: {
                UserType.PROPONENT: PackageStatus.SUBMITTED.value,
                UserType.STAFF: (PackageStatus.NEW_SUBMISSION.value if version == 1
                                 else PackageStatus.RESUBMITTED.value)
            },
            PackageStatus.INTERNAL_VERIFICATION.value: {
                UserType.PROPONENT: PackageStatus.SUBMITTED.value,
                UserType.STAFF: PackageStatus.INTERNAL_VERIFICATION.value
            },
            PackageStatus.VERIFIED.value: {
                UserType.PROPONENT: PackageStatus.SUBMITTED.value,
                UserType.STAFF: PackageStatus.VERIFIED.value
            },
            PackageStatus.PENDING_ACKNOWLEDGEMENT.value: {
                UserType.PROPONENT: PackageStatus.SUBMITTED.value,
                UserType.STAFF: PackageStatus.PENDING_ACKNOWLEDGEMENT.value
            },
            PackageStatus.READY_FOR_ACKNOWLEDGEMENT.value: {
                UserType.PROPONENT: PackageStatus.SUBMITTED.value,
                UserType.STAFF: PackageStatus.READY_FOR_ACKNOWLEDGEMENT.value
            },
            PackageStatus.ACKNOWLEDGED.value: {
                UserType.PROPONENT: PackageStatus.ACKNOWLEDGED.value,
                UserType.STAFF: PackageStatus.ACKNOWLEDGED.value
            },
            PackageStatus.READY_FOR_APPROVAL.value: {
                UserType.PROPONENT: PackageStatus.ACKNOWLEDGED.value,
                UserType.STAFF: PackageStatus.READY_FOR_APPROVAL.value
            },
            PackageStatus.APPROVED.value: {
                UserType.PROPONENT: PackageStatus.APPROVED.value,
                UserType.STAFF: PackageStatus.APPROVED.value
            },
            PackageStatus.NOT_APPROVED.value: {
                UserType.PROPONENT: PackageStatus.NOT_APPROVED.value,
                UserType.STAFF: PackageStatus.NOT_APPROVED.value
            },
            # end work related package statuses
            PackageStatus.PARTIALLY_COMPLETED.value: {
                UserType.PROPONENT: PackageStatus.PARTIALLY_COMPLETED.value,
                UserType.STAFF: PackageStatus.CREATED.value if version == 1 else ''
            },
            PackageStatus.COMPLETED.value: {
                UserType.PROPONENT: PackageStatus.COMPLETED.value,
                UserType.STAFF: PackageStatus.CREATED.value if version == 1 else ''
            },
            PackageStatus.UNDER_REVIEW.value: {
                UserType.PROPONENT: PackageStatus.UNDER_REVIEW.value,
                UserType.STAFF: PackageStatus.UNDER_REVIEW.value
            },
            PackageStatus.UNDER_CONSULTATION_CHECK.value: {
                UserType.PROPONENT: PackageStatus.UNDER_CONSULTATION_CHECK.value,
                UserType.STAFF: PackageStatus.UNDER_CONSULTATION_CHECK.value
            },
            PackageStatus.CC_AWAITING_MANAGER_APPROVAL.value: {
                UserType.PROPONENT: PackageStatus.UNDER_CONSULTATION_CHECK.value,
                UserType.STAFF: PackageStatus.AWAITING_MANAGER_APPROVAL.value
            },
            PackageStatus.MP_AWAITING_MANAGER_APPROVAL.value: {
                UserType.PROPONENT: PackageStatus.UNDER_REVIEW.value,
                UserType.STAFF: PackageStatus.AWAITING_MANAGER_APPROVAL.value
            },
            PackageStatus.IEM_AWAITING_MANAGER_APPROVAL.value: {
                UserType.PROPONENT: PackageStatus.UNDER_REVIEW.value,
                UserType.STAFF: PackageStatus.AWAITING_MANAGER_APPROVAL.value
            },
            PackageStatus.REVIEW_REJECTED.value: {
                UserType.PROPONENT: PackageStatus.REVISION_REQUIRED.value,
                UserType.STAFF: PackageStatus.REVIEW_REJECTED.value
            },
            PackageStatus.REVISION_REQUIRED.value: {
                UserType.PROPONENT: PackageStatus.REVISION_REQUIRED.value,
                UserType.STAFF: NonCanonicalPackageStatus.REVISION_REQUESTED.value
            },
            PackageStatus.SATISFIED.value: {
                UserType.PROPONENT: PackageStatus.NO_REVISION_REQUIRED.value,
                UserType.STAFF: PackageStatus.SATISFIED.value
            },
            PackageStatus.REVIEWED.value: {
                UserType.PROPONENT: PackageStatus.REVIEWED.value,
                UserType.STAFF: PackageStatus.REVIEWED.value
            },
            PackageStatus.WITHDRAWN.value: {
                UserType.PROPONENT: PackageStatus.WITHDRAWN.value,
                UserType.STAFF: PackageStatus.WITHDRAWN.value
            }
        }

    @staticmethod
    def _map_canonical_statuses(package, user_type, package_status_mapping):
        """Map canonical statuses based on user type."""
        new_status = []
        for status in package.status:
            status_value = status.value if hasattr(status, 'value') else status
            if status_value in package_status_mapping:
                mapped_status = package_status_mapping[status_value][user_type]
                if mapped_status:
                    new_status.append(mapped_status)
            else:
                new_status.append(status_value)
        return new_status

    @staticmethod
    def _check_item_conditions(package):
        """Check for revision required and updated submission conditions."""
        has_revision_required = False
        has_updated_submission = False

        for item in package.items:
            if item.status.value == 'REVISION_REQUIRED':
                has_revision_required = True

            for submission in item.submissions:
                if submission.is_updated and submission.status.value == 'SUBMITTED':
                    has_updated_submission = True
                    break

            if has_revision_required and has_updated_submission:
                break

        return has_revision_required, has_updated_submission

    @staticmethod
    def _add_noncanonical_statuses(new_status, has_open_update_request, has_updated_submission,
                                   has_revision_required, user_type):
        """Add noncanonical statuses to the status list.

        Suppression rules (D16):
        - When UPDATED is present, UPDATE_REQUESTED and REVISION are hidden.
        - Per-audience: entity sees REVISION_REQUIRED, EAO sees REVISION_REQUESTED.
        """
        if has_updated_submission:
            # Updated suppresses both Update Requested and Revision overlays
            new_status.append(NonCanonicalPackageStatus.UPDATED.value)
        else:
            if has_open_update_request:
                new_status.append(NonCanonicalPackageStatus.UPDATE_REQUESTED.value)
            if has_revision_required:
                status_to_add = (NonCanonicalPackageStatus.REVISION_REQUIRED.value
                                 if user_type == UserType.PROPONENT
                                 else NonCanonicalPackageStatus.REVISION_REQUESTED.value)
                new_status.append(status_to_add)

    @staticmethod
    def _deduplicate_statuses(statuses):
        """Deduplicate statuses while preserving order."""
        seen = set()
        deduped = []
        for status in statuses:
            if status and status not in seen:
                seen.add(status)
                deduped.append(status)
        return deduped

    @staticmethod
    def _sort_statuses(statuses):
        """Sort statuses in canonical D9 order."""
        max_index = len(CANONICAL_STATUS_ORDER)
        return sorted(
            statuses,
            key=lambda s: CANONICAL_STATUS_ORDER.index(s) if s in CANONICAL_STATUS_ORDER else max_index
        )

    @staticmethod
    def calculate_package_statuses(package, user_type):
        """Calculate complete package status list including noncanonical statuses.

        Optimized to process all data in a single pass to avoid unnecessary iterations.
        Includes canonical status mapping based on user type and version.

        Args:
            package: Package model object with items and update_requests loaded
            user_type: UserType enum value (STAFF or PROPONENT)

        Returns:
            list: Complete list of status strings including noncanonical statuses
        """
        if user_type not in [UserType.PROPONENT, UserType.STAFF]:
            return [status.value if hasattr(status, 'value') else status for status in package.status]

        version = package.version.version if package.version else 1
        package_status_mapping = PackageService._get_status_mapping(version)
        new_status = PackageService._map_canonical_statuses(package, user_type, package_status_mapping)

        has_revision_required, has_updated_submission = PackageService._check_item_conditions(package)
        has_open_update_request = any(
            ur.active and ur.status == 'OPEN' and ur.type == UpdateRequestType.UPDATE
            for ur in package.update_requests
        )
        has_open_review_request = any(
            ur.active and ur.status == 'OPEN' and ur.type == UpdateRequestType.REVIEW
            for ur in package.update_requests
        )
        # A REVIEW-type open request also signals revision required (for the new version package)
        if has_open_review_request:
            has_revision_required = True

        PackageService._add_noncanonical_statuses(
            new_status, has_open_update_request, has_updated_submission,
            has_revision_required, user_type
        )

        return PackageService._sort_statuses(PackageService._deduplicate_statuses(new_status))

    @classmethod
    def get_package_by_id(cls, package_id):
        """Get package by id."""
        authorization.has_access_to_package(package_id)
        package = PackageModel.get_package_by_id_with_items(package_id)
        return package

    @classmethod
    def create_new_package_from_original(cls, current_package_id, session):
        """Create a new package version."""
        return PackageVersionService.create_new_package_version(current_package_id, session)

    @classmethod
    def create_first_package(cls, account_project_id, request_data):
        """Create a new package."""
        with session_scope() as session:
            package_type = PackageTypeModel.find_by_name(
                request_data.get("type"))

            if not package_type:
                raise BadRequestError(f"Invalid package type: {package_type}")

            package = cls._create_package(
                session, account_project_id, request_data, package_type)

            # Create package version only if versioning is enabled for this package type
            # Some package types (e.g., Additional Information) don't require versioning
            # as they are simple document uploads that don't follow the review/approval workflow
            if package_type.versioning_enabled:
                package_version = cls._create_package_version(
                    session, original_package_id=package.id, version=1)
                package.version_id = package_version.id
                session.add(package)

            cls._create_package_metadata(
                session, package.id, request_data.get("metadata"))
            cls._create_items(session, package.id, package_type)
            session.commit()
        return PackageModel.find_by_id(package.id)

    @staticmethod
    def _create_package(session, account_project_id, request_data, package_type):
        """Create a new package."""
        current_app.logger.info(f"Creating a new package for account project {account_project_id}")
        package_data = {
            "account_project_id": account_project_id,
            "name": request_data.get("name"),
            "description": request_data.get("description"),
            "type_id": package_type.id,
        }
        if status := request_data.get("status"):
            package_data["status"] = status

        # Use account_project_work_id from request if provided
        if request_data.get("account_project_work_id"):
            package_data["account_project_work_id"] = request_data.get("account_project_work_id")
            # Set NEW status for work-related packages
            if not package_data.get("status"):
                package_data["status"] = [PackageStatus.NEW.value]
                work_id = request_data.get('account_project_work_id')
                current_app.logger.info(
                    f"Setting NEW status for work-related package with work_id: {work_id}"
                )
            current_app.logger.info(
                f"Using account_project_work_id from request: {request_data.get('account_project_work_id')}"
            )
        # Otherwise, try to find it automatically if package type has a phase
        elif package_type.phase_id:
            # Find the account_project_work that matches this phase
            account_project_works = AccountProjectWorkModel.find_by_account_project_id(account_project_id)
            for apw in account_project_works:
                if apw.work and apw.work.current_phase_id == package_type.phase_id:
                    package_data["account_project_work_id"] = apw.id
                    current_app.logger.info(
                        f"Auto-associating package with work {apw.work_id} (phase: {package_type.phase_id})"
                    )
                    break

        package = PackageModel(**package_data)
        session.add(package)
        session.flush()
        current_app.logger.info(f"Created package {package.id} for account project {account_project_id}")
        return package

    @classmethod
    def create_new_package_version_with_contacts(cls, package_id):
        """Create a new package version with contact information and cleanup."""
        with session_scope() as session:
            current_app.logger.info(f"Creating new package version for package {package_id}")

            original_package = PackageModel.find_by_id(package_id)
            if not original_package:
                raise ResourceNotFoundError(f"Package {package_id} not found")

            new_package = cls.create_new_package_from_original(package_id, session)

            PackageVersionService.copy_contact_information(original_package, new_package)

            PackageVersionService.deactivate_update_requests(original_package.id, session, original_package)

            PackageVersionService.create_email_queue(
                new_package.id,
                MANAGEMENT_PLAN_RESUBMISSION_REQUEST_EMAIL_TEMPLATE,
                session=session
            )
            # Set up the submitter information from the original package
            if original_package.submitted_by:
                # Get the user by auth_guid
                user = User.get_by_guid(original_package.submitted_by)
                if user:
                    new_package.submitted_by = user.auth_guid

            # Update item and package statuses
            items_to_update = cls._get_items_to_mark_review_not_completed(original_package.items)
            cls._update_items_status(items_to_update, ItemStatus.REVIEW_NOT_COMPLETED.value, session)
            cls._update_package_status(original_package.id, session, original_package)

            ActivityLogService.log_activity(
                entity_id=(
                    original_package.version.original_package_id
                    if original_package.version else original_package.id
                ),
                action=ActivityActionType.RESUBMISSION_INVITATION.value,
                entity_version=original_package.version.version if original_package.version else 1,
                session=session
            )

            session.add(new_package)
            session.flush()

            current_app.logger.info(f"New package version created for {new_package.name}")
            return new_package

    @classmethod
    def _create_resubmission_email_queue(cls, package_id):
        """Create an email queue record for resubmission request."""
        SubmitEmailQueueService.queue_package_email(
            package_id,
            MANAGEMENT_PLAN_RESUBMISSION_REQUEST_EMAIL_TEMPLATE,
        )

    @staticmethod
    def _create_package_metadata(session, package_id, metadata):
        """Create package metadata."""
        current_app.logger.info(f"Creating metadata for package {package_id}")
        package_metadata = PackageMetadataModel(
            package_id=package_id, json=metadata
        )
        session.add(package_metadata)
        current_app.logger.info(f"Created metadata for package {package_id}")

    @staticmethod
    def _update_package_metadata(session, package_id, metadata_updates):
        """Update specific fields in package metadata by package ID."""
        # Retrieve the existing package metadata
        package_metadata = PackageMetadataModel.get_by_package_id(package_id)

        if not package_metadata:
            raise ValueError(f"Package metadata for package_id {package_id} does not exist.")

        metadata = package_metadata.json or {}
        new_metadata = {**metadata, **metadata_updates}

        # Add the updated metadata back to the session
        package_metadata.json = new_metadata
        session.add(package_metadata)

    @classmethod
    def _create_package_version(cls, session, original_package_id, version=1):
        """Create a new package version."""
        current_app.logger.info(f"Creating a new package version for package {original_package_id}")
        package_version = PackageVersionModel(
            original_package_id=original_package_id,
            version=version
        )
        session.add(package_version)
        session.flush()
        current_app.logger.info(f"Created package version {package_version.id} for package {original_package_id}")
        return package_version

    @classmethod
    def get_all_package_versions_by_original_package_id(cls, original_package_id):
        """Get all package versions by original package id."""
        all_package_versions = PackageVersionModel.get_all_by_original_package_id(original_package_id)
        return all_package_versions

    @staticmethod
    def _create_items(session, package_id, package_type):
        """Create items for the package."""
        current_app.logger.info(f"Creating items for package {package_id}")
        package_item_types = PackageItemTypeModel.get_by_package_type_id(package_type.id)

        item_type_to_package_item_type = {
            pit.item_type_id: pit for pit in package_item_types
        }

        for item_type in package_type.item_types:
            current_app.logger.info(f"Creating item for package {package_id} with item type {item_type.name}")
            package_item_type = item_type_to_package_item_type.get(
                item_type.id)
            if package_item_type:
                item = ItemModel(
                    package_id=package_id,
                    type_id=item_type.id,
                    sort_order=package_item_type.sort_order
                )
                session.add(item)
                (current_app.logger
                 .info(f"Created item {item.id} for package {package_id} with item type {item_type.name}"))
        current_app.logger.info(f"Created items for package {package_id}")
        session.flush()

    @classmethod
    def _get_required_items(cls, package):
        """Get required items for a package based on package_item_types configuration."""
        package_item_types = PackageItemTypeModel.get_by_package_type_id(package.type_id)
        required_item_type_ids = {
            pit.item_type_id for pit in package_item_types if pit.is_required
        }
        return [item for item in package.items if item.type_id in required_item_type_ids]

    @classmethod
    def _get_and_validate_complete_package(cls, package_id) -> PackageModel:
        """Retrieve and validate that all required items in the package are completed."""
        package = PackageModel.find_by_id(package_id)
        if package.submitted_on:
            return cls._validate_package_for_resubmit(package)

        cls._validate_completeness(package)
        current_app.logger.info(f"Package {package_id} is ready to submit")
        return package

    @classmethod
    def _validate_completeness(cls, package):
        """Validate that required items have at least one document submission.

        Shared validation used for first submission and work-package
        pre-acknowledgement resubmission. Checks that each required item
        has at least one document submission rather than relying on item
        status, which can be in many valid states (ACKNOWLEDGED, VERIFIED, etc.)
        during resubmission.
        """
        document_submissions = cls._get_document_submissions_from_package(package)
        if not document_submissions:
            current_app.logger.info(f"Package {package.id} has no documents")
            raise BadRequestError(
                "You must have at least one file uploaded to be able to submit your package."
            )

        required_items = cls._get_required_items(package)
        items_missing_documents = [
            item for item in required_items
            if item.type.submission_method == SubmissionMethod.DOCUMENT_UPLOAD
            and not any(
                sub.type == SubmissionType.DOCUMENT
                and not sub.deleted
                for sub in item.submissions
            )
        ]

        if items_missing_documents:
            current_app.logger.info(
                f"Package {package.id} has required items without documents: "
                f"{[item.type.name for item in items_missing_documents]}"
            )
            raise BadRequestError(
                "All required items must have at least one document before submitting the package"
            )

    @classmethod
    def _validate_package_for_resubmit(cls, package) -> PackageModel:
        """Validate resubmission eligibility using the five-rule model (D17).

        Rules:
        1. Work packages before acknowledgement: free resubmit with completeness validation.
        2. Work packages after acknowledgement: requires open update request.
        3. MP/IEM packages: always requires open update request.
        4. After failed consultation check: existing update request satisfies rule 3.
        5. After failed MP review / IPD Not Approved: new version goes through
           first-submission path (submitted_on is None), not this method.
        """
        current_app.logger.info(f"Validating package {package.id} for resubmission")
        if not package.submitted_on:
            raise BadRequestError("Cannot resubmit a package that has not been submitted")

        # Terminal state guards
        if PackageStatus.APPROVED.value in package.status:
            raise BadRequestError("Cannot resubmit a package that has been approved")
        if PackageStatus.REJECTED.value in package.status:
            raise BadRequestError("Cannot resubmit a package that has been rejected")
        if PackageStatus.NOT_APPROVED.value in package.status:
            raise BadRequestError("Cannot resubmit a package that has not been approved")

        is_work_package = bool(package.account_project_work_id)
        is_acknowledged = PackageStatus.ACKNOWLEDGED.value in package.status

        # Collect non-closed update requests
        open_update_requests = [
            request for request in package.update_requests
            if request.status != UpdateRequestStatus.ACCEPTED.value
            and request.active
        ]

        if is_work_package:
            # Rule 1: work package pre-acknowledgement — free resubmit with completeness
            if not is_acknowledged:
                cls._validate_completeness(package)
                current_app.logger.info(
                    f"Work package {package.id} passes pre-ack resubmission"
                )
                return package

            # Rule 2: work package post-acknowledgement — requires update request
            if not open_update_requests:
                raise BadRequestError(
                    "Cannot resubmit an acknowledged package without an open update request"
                )
            cls._validate_no_empty_submissions(package)
        else:
            # Rule 3: MP/IEM packages — always require update request
            if not open_update_requests:
                raise BadRequestError(
                    "Cannot resubmit a package without an open update request"
                )
            cls._validate_no_empty_submissions(package)

        current_app.logger.info(f"Package {package.id} is ready to resubmit")
        return package

    @staticmethod
    def _update_package_status(package_id, session, package=None):
        """Update the status of the package based on the statuses of its items."""
        PackageItemQueries.update_package_status(package_id, session, package)

    @staticmethod
    def _get_items_to_mark_review_not_completed(items):
        active_review_statuses = (ItemStatus.UNDER_REVIEW, ItemStatus.UNDER_CONSULTATION_CHECK)
        items_to_update = [i for i in items if i.status in active_review_statuses]

        is_under_consultation_check = any(
            i.status == ItemStatus.UNDER_CONSULTATION_CHECK for i in items
        )
        if is_under_consultation_check:
            items_to_update.extend(
                i for i in items
                if i.status == ItemStatus.SUBMITTED and
                i.type.name == SubmissionItemType.MANAGEMENT_PLAN_FORM.value
            )
        return items_to_update

    @staticmethod
    def _update_items_status(items, status, session):
        """Update status of all items in the package."""
        for item in items:
            item.status = status
            session.add(item)
        session.flush()

    @staticmethod
    def _update_review_item(review_item, data, session):
        """Update the status of all items in the package."""
        review_item.status = data.get('status')
        review_item.review_start_date = data.get('review_start_date')
        session.add(review_item)

    @staticmethod
    def _update_cr_status(items, data, session):
        """Update the status of all items in the package."""
        cr_item = next((item for item in items
                        if item.type.name == SubmissionItemType.CONSULTATION_RECORD.value), None)
        if not cr_item:
            raise BadRequestError("Consultation record not found in package")
        if cr_item.status != ItemStatus.SUBMITTED:
            raise BadRequestError("Consultation record in package is not submitted")
        cr_item.status = data.get('status')
        cr_item.review_start_date = data.get('review_start_date')
        session.add(cr_item)

    @staticmethod
    def _update_package_submission_details(package, session):
        """Update package submission details."""
        current_app.logger.info(f"Updating submission details for package {package.id}")
        package.submitted_on = datetime.now(UTC)
        package.submitted_by = TokenInfo.get_username()

        session.add(package)

    @staticmethod
    def _update_submission_status(package, status, session):
        """Update package submission details."""
        if status not in SubmissionStatus.__members__:
            raise BadRequestError("Invalid status")
        for item in package.items:
            for submission in item.submissions:
                if item.type.name == SubmissionItemType.CONSULTATION_RECORD.value \
                        and submission.status == SubmissionStatus.REJECTED:
                    # Skip updating rejected consultation record submissions
                    continue
                submission.status = status
                session.add(submission)

    @staticmethod
    def _update_submission_status_on_resubmit(package, session):
        """Update only PENDING submission statuses to SUBMITTED during resubmission.

        This preserves the status of submissions that have already been processed by staff:
        - VERIFIED, APPROVED, REJECTED, ACKNOWLEDGED statuses are preserved
        - SUBMITTED statuses are preserved (no unnecessary updates)
        - Only PENDING submissions are updated to SUBMITTED
        """
        for item in package.items:
            for submission in item.submissions:
                if submission.status == SubmissionStatus.PENDING:
                    submission.status = SubmissionStatus.SUBMITTED
                    session.add(submission)
        current_app.logger.info(f"Updated PENDING submissions to SUBMITTED for package {package.id}")

    @staticmethod
    def _deactivate_replaced_submissions(package, session):
        """Deactivate replaced submissions."""
        current_app.logger.info(f"Deactivating pending replacement submissions for package {package.id}")
        submissions = [submission for item in package.items for submission in item.submissions]
        pending_submissions = set(submission.root_submission_id for item in package.items for submission
                                  in item.submissions if submission.status == SubmissionStatus.PENDING)

        for submission in submissions:
            if submission.status != SubmissionStatus.PENDING and submission.root_submission_id in pending_submissions:
                submission.active = False
                session.add(submission)

    @staticmethod
    def _deactivate_revision_required_requests(package, session):
        """Move carried REVIEW-type requests to pending review on a within-package resubmission."""
        current_app.logger.info(f"Deactivating revision required requests for package {package.id}")
        revision_required_requests = [request for request in package.update_requests
                                      if request.type == UpdateRequestType.REVIEW]
        for request in revision_required_requests:
            request.status = UpdateRequestStatus.PENDING_REVIEW.value
            session.add(request)

    @staticmethod
    def _close_carried_review_requests(package, session):
        """Close REVIEW-type update requests carried into a new package version on first submission."""
        current_app.logger.info(f"Closing carried review requests for package {package.id}")
        carried_review_requests = [request for request in package.update_requests
                                   if request.type == UpdateRequestType.REVIEW]
        for request in carried_review_requests:
            request.status = UpdateRequestStatus.CLOSED.value
            request.active = False
            session.add(request)

    @staticmethod
    def _update_update_requests(session, package, status, active=True):
        """Update package submission details."""
        current_app.logger.info(f"Updating update requests for package {package.id}")
        revision_required_requests = [request for request in package.update_requests
                                      if request.type == UpdateRequestType.UPDATE]
        for request in revision_required_requests:
            request.status = status
            request.active = active
            session.add(request)

    @staticmethod
    def _get_document_submissions_from_package(package):
        """Get submissions from package."""
        submissions = []
        for item in package.items:
            for submission in item.submissions:
                if submission.type == SubmissionType.DOCUMENT:
                    submissions.append(submission)
        return submissions

    @classmethod
    def submit_package(cls, package_id):
        """Submit the package by updating its status and items."""
        cls._validate_account_user()
        with session_scope() as session:
            package = cls._get_and_validate_complete_package(package_id)
            authorization.check_has_permissions_on_project(
                permissions=[ProponentPermissionsEnum.SUBMIT_PACKAGE.value],
                account_project_ids=[package.account_project_id]
            )
            if GeoService.has_unapproved_uploads_for_package(package_id):
                raise BadRequestError(
                    "All geospatial files must be reviewed and approved before "
                    "submitting the package to the EAO."
                )
            if package.submitted_on:
                submitted_package: PackageModel = cls._resubmit_package(package, session)
            else:
                submitted_package: PackageModel = cls._submit_package(package, session)

            return submitted_package

    @classmethod
    def _submit_package(cls, package, session):
        """Submit the package by updating its status and items."""
        # For work-related packages with IN_PROGRESS status, explicitly set to SUBMITTED
        if package.account_project_work_id and PackageStatus.IN_PROGRESS.value in package.status:
            package.status = [PackageStatus.SUBMITTED.value]
            session.add(package)
            current_app.logger.info(
                f"Changed status from IN_PROGRESS to SUBMITTED for work-related package {package.id}"
            )

        cls._update_items_status(
            package.items, ItemStatus.SUBMITTED.value, session)
        cls._update_submission_status(package, SubmissionStatus.SUBMITTED.value, session)
        cls._update_package_submission_details(package, session)
        cls._close_carried_review_requests(package, session)
        cls._create_email_queue_record(package, session)
        cls._log_activity_submission(package, ActivityActionType.SUBMITTED_TO_EAO.value, session)

        # For work-related packages, update status from submissions
        if package.account_project_work_id:
            PackageSubmissionQueries.update_package_status_from_submissions(package.id, session, package)
        else:
            cls._update_package_status(package.id, session, package)

        return package

    @classmethod
    def _resubmit_package(cls, package, session):
        """Submit the package by updating its status and items."""
        current_app.logger.info(f"Resubmitting package {package.id}")
        if package.completed_on:
            raise BadRequestError("Cannot resubmit a package that has been completed")
        cls._update_package_submission_details(package, session)

        cls._deactivate_replaced_submissions(package, session)
        cls._create_email_queue_record(package, session)
        cls._update_submission_status_on_resubmit(package, session)
        cls._deactivate_revision_required_requests(package, session)
        cls._update_update_requests(session, package, status=UpdateRequestStatus.PENDING_REVIEW.value)
        cls._deactivate_fail_reviews(package, session)
        cls._log_activity_submission(package, ActivityActionType.UPDATED_SUBMISSION.value, session)

        # Update package status from submissions for work-related packages
        # Only update if the package is not already acknowledged
        if package.account_project_work_id and PackageStatus.ACKNOWLEDGED not in package.status:
            PackageSubmissionQueries.update_package_status_from_submissions(package.id, session, package)

        return package

    @classmethod
    def accept_update_request(cls, package_id, update_request_id):
        """Submit the package by updating its status and items."""
        with session_scope() as session:
            package = cls.get_package_by_id(package_id)
            update_request = UpdateRequestModel.find_by_id(update_request_id)
            cls._validate_accept_update_request(package, update_request)

            # Validate GIS role if update request is for GIS documents
            cls._validate_gis_role_for_existing_update_request(package, update_request)

            update_request = UpdateRequestModel.find_by_id(update_request_id)
            update_request.status = UpdateRequestStatus.ACCEPTED.value
            update_request.active = False
            session.add(update_request)
            cls._reset_is_updated_for_accepted_request(package, update_request, session)
            session.flush()

            return package

    @classmethod
    def withdraw_update_request(cls, package_id, update_request_id):
        """Withdraw an update request by setting its status to CLOSED."""
        with session_scope() as session:
            package = cls.get_package_by_id(package_id)
            update_request = UpdateRequestModel.find_by_id(update_request_id)
            cls._validate_withdraw_update_request(package, update_request)

            # Validate GIS role if update request is for GIS documents
            cls._validate_gis_role_for_existing_update_request(package, update_request)

            update_request = UpdateRequestModel.find_by_id(update_request_id)
            update_request.status = UpdateRequestStatus.CLOSED.value
            update_request.active = False
            session.add(update_request)
            session.flush()
            return package

    @classmethod
    def _validate_accept_update_request(cls, package, update_request):
        """Validate the accept update request."""
        if not package:
            raise BadRequestError("Package not found")

        if not update_request:
            raise BadRequestError("Update request not found")
        if update_request.submission_package_id != package.id:
            raise BadRequestError("Update request does not belong to the specified package")
        if update_request.status != UpdateRequestStatus.PENDING_REVIEW.value:
            raise BadRequestError("Update request is not pending review")

    @classmethod
    def _validate_withdraw_update_request(cls, package, update_request):
        """Validate the withdraw update request."""
        if not package:
            raise BadRequestError("Package not found")

        if not update_request:
            raise BadRequestError("Update request not found")
        if update_request.submission_package_id != package.id:
            raise BadRequestError("Update request does not belong to the specified package")
        if package.type and package.type.name in MANAGEMENT_PLAN_RELATED_TYPES:
            raise BadRequestError("Update requests for this package type cannot be withdrawn")
        if update_request.status != UpdateRequestStatus.OPEN.value:
            raise BadRequestError("Update request can only be withdrawn when status is OPEN")

    @staticmethod
    def _log_activity_submission(package, action, session):
        """Log activity for package submission."""
        ActivityLogService.log_activity(
            entity_id=package.version.original_package_id if package.version else package.id,
            action=action,
            actor_type=ActorTypeEnum.ENTITY.value,
            entity_version=package.version.version if package.version else 1,
            session=session
        )

    @classmethod
    def _deactivate_fail_reviews(cls, package, session):
        """Deactivate all fail reviews for the package."""
        current_app.logger.info(f"Deactivating fail reviews for package {package.id}")
        fail_reviews = [item.review for item in package.items
                        if item.review and item.review.status == SubmissionReviewStatus.REJECTED]
        for review in fail_reviews:
            review.active = False
            session.add(review)

    @classmethod
    def acknowledge_package(cls, package_id):
        """Acknowledge the package."""
        with session_scope() as session:
            package = cls.get_package_by_id(package_id)
            if not package:
                raise BadRequestError("Package not found")

            # Acknowledgement only applies to package types that follow the staged
            # approval workflow (approval types A/B/C).
            if package.type.approval_type not in (
                PackageApprovalType.A,
                PackageApprovalType.B,
                PackageApprovalType.C,
            ):
                raise BadRequestError("This package type does not support acknowledgement.")

            for item in package.items:
                item.status = ItemStatus.ACKNOWLEDGED
                session.add(item)
                # For non-versioned packages, we acknowledge all documents
                if not package.type.versioning_enabled:
                    for submission in item.submissions:
                        if submission.type == SubmissionType.DOCUMENT:
                            submission.status = SubmissionStatus.ACKNOWLEDGED
                            session.add(submission)

            if package.type.approval_type == PackageApprovalType.C:
                package.status = [PackageStatus.ACKNOWLEDGED.value, PackageStatus.READY_FOR_APPROVAL.value]
            else:
                package.status = [PackageStatus.ACKNOWLEDGED.value]
            session.add(package)
            if package.type.name != PackageTypeEnum.MANAGEMENT_PLAN.value:
                SubmitEmailQueueService.queue_package_email(
                    package.id,
                    SUBMISSION_ACKNOWLEDGED_CONFIRMATION_EMAIL_TEMPLATE,
                    session=session,
                    package=package
                )
            session.flush()
            return package

    @staticmethod
    def _has_open_update_requests(package):
        """Check if package has open or pending review update requests."""
        return any(
            ur.active and ur.status in [
                UpdateRequestStatus.OPEN.value,
                UpdateRequestStatus.PENDING_REVIEW.value
            ]
            for ur in package.update_requests
        )

    @staticmethod
    def _reset_is_updated_for_accepted_request(package, accepted_request, session):
        """Reset is_updated on submissions whose item types have no remaining OPEN update requests."""
        # Subquery: item type IDs that have an OPEN update request for this package
        open_item_type_subquery = (
            session.query(func.unnest(UpdateRequestModel.submission_item_types).label('type_id'))
            .filter(
                UpdateRequestModel.submission_package_id == package.id,
                UpdateRequestModel.active.is_(True),
                UpdateRequestModel.status.in_([
                    UpdateRequestStatus.OPEN.value,
                    UpdateRequestStatus.PENDING_REVIEW.value,
                ]),
            )
            .subquery()
        )

        # Find item type IDs from submissions with is_updated=True that have no OPEN update request
        items_without_open_request = (
            session.query(ItemModel.type_id)
            .join(Submission, Submission.item_id == ItemModel.id)
            .filter(
                ItemModel.package_id == package.id,
                Submission.is_updated.is_(True),
                ~ItemModel.type_id.in_(session.query(open_item_type_subquery.c.type_id)),
            )
            .distinct()
            .all()
        )

        # Combine: items without open request + the accepted request's item types
        types_to_reset = {row[0] for row in items_without_open_request}
        types_to_reset.update(accepted_request.submission_item_types or [])

        if not types_to_reset:
            return

        # Reset is_updated to False for all matching submissions
        session.query(Submission).filter(
            Submission.item_id == ItemModel.id,
            ItemModel.package_id == package.id,
            ItemModel.type_id.in_(types_to_reset),
            Submission.is_updated.is_(True),
        ).update({Submission.is_updated: False}, synchronize_session='fetch')

    @classmethod
    def approve_package(cls, package_id):
        """Approve the package.

        Only Team Leads and users with full_access role can approve packages.
        Team Members can view, verify, acknowledge, and request updates.
        """
        # Require Team Lead or full_access role for approval
        authorization.require_team_lead_access()

        with session_scope() as session:
            package = cls.get_package_by_id(package_id)
            if not package:
                raise BadRequestError("Package not found")

            # Approval only applies to Type C packages.
            if package.type.approval_type != PackageApprovalType.C:
                raise BadRequestError("This package type does not support approval.")

            # Check for open update requests
            if cls._has_open_update_requests(package):
                raise BadRequestError(
                    "Package cannot be approved while there are open update requests. "
                    "Please accept or withdraw all update requests first."
                )

            # Approve all documents
            for item in package.items:
                item.status = ItemStatus.APPROVED
                session.add(item)
                for submission in item.submissions:
                    if submission.type == SubmissionType.DOCUMENT:
                        submission.status = SubmissionStatus.APPROVED
                        session.add(submission)

            package.status = [PackageStatus.APPROVED.value]
            session.add(package)
            session.flush()
            return package

    @classmethod
    def refuse_package(cls, package_id, decision_date):
        """Do not approve the package."""
        with session_scope() as session:
            package = cls.get_package_by_id(package_id)
            if not package:
                raise BadRequestError("Package not found")

            # Check for open update requests
            if cls._has_open_update_requests(package):
                raise BadRequestError(
                    "Package cannot be rejected while there are open update requests. "
                    "Please accept or withdraw all update requests first."
                )

            # Remove all document statuses
            for item in package.items:
                item.status = ItemStatus.NOT_APPROVED
                session.add(item)
                for submission in item.submissions:
                    if submission.type == SubmissionType.DOCUMENT:
                        submission.status = None
                        session.add(submission)

            package.status = [PackageStatus.NOT_APPROVED.value]
            package.decision_date = decision_date
            session.add(package)

            # Cancel all open update requests
            for update_request in package.update_requests:
                update_request.status = UpdateRequestStatus.CLOSED.value
                update_request.active = False
                session.add(update_request)

            # Create new package version
            new_package = cls.create_new_package_from_original(package_id, session)
            if package.submitted_by:
                user = User.get_by_guid(package.submitted_by)
                if user:
                    new_package.submitted_by = user.auth_guid
            new_package.status = [PackageStatus.REVISION_REQUIRED]

            # Add works
            new_package.account_project_work = package.account_project_work

            session.flush()
            return new_package

    @classmethod
    def withdraw_package(cls, package_id):
        """Withdraw a submitted package."""
        cls._validate_account_user()
        with session_scope() as session:
            package = cls.get_package_by_id(package_id)
            cls._validate_package_for_withdrawal(package)
            authorization.check_has_permissions_on_project(
                permissions=[ProponentPermissionsEnum.SUBMIT_PACKAGE.value],
                account_project_ids=[package.account_project_id]
            )

            # Update package status to WITHDRAWN
            package.status = [PackageStatus.WITHDRAWN]
            session.add(package)

            # Log withdrawal activity
            cls._log_activity_submission(package, ActivityActionType.SUBMITTED_TO_EAO.value, session)

            # Create new package version (Package 2)
            new_package = PackageVersionService.create_new_package_version(package_id, session)
            SubmitEmailQueueService.queue_package_email(
                new_package.id,
                SUBMISSION_WITHDRAWN_CONFIRMATION_EMAIL_TEMPLATE,
                session=session,
                package=new_package
            )
            session.flush()
            return package

    @classmethod
    def _validate_package_for_withdrawal(cls, package):
        """Validate that a package can be withdrawn."""
        if not package:
            raise ResourceNotFoundError("Package not found")

        if not package.type.versioning_enabled:
            raise BadRequestError("Cannot withdraw a package that does not have versioning enabled")

        if not package.submitted_on:
            raise BadRequestError("Cannot withdraw a package that has not been submitted")

        # Check if package is in a withdrawable status
        # Proponents see SUBMITTED for: SUBMITTED, INTERNAL_VERIFICATION, VERIFIED,
        # PENDING_ACKNOWLEDGEMENT, READY_FOR_ACKNOWLEDGEMENT
        # Proponents see ACKNOWLEDGED for: ACKNOWLEDGED, READY_FOR_APPROVAL
        withdrawable_statuses = [
            PackageStatus.SUBMITTED,
            PackageStatus.INTERNAL_VERIFICATION,
            PackageStatus.VERIFIED,
            PackageStatus.PENDING_ACKNOWLEDGEMENT,
            PackageStatus.READY_FOR_ACKNOWLEDGEMENT,
            PackageStatus.ACKNOWLEDGED,
            PackageStatus.READY_FOR_APPROVAL
        ]

        if not any(status in package.status for status in withdrawable_statuses):
            raise BadRequestError(
                "Package can only be withdrawn when it is in Submitted or Acknowledged status"
            )

        # Cannot withdraw if already in terminal states
        if PackageStatus.APPROVED in package.status:
            raise BadRequestError("Cannot withdraw an approved package")

        if PackageStatus.NOT_APPROVED in package.status:
            raise BadRequestError("Cannot withdraw a package that has not been approved")

        if PackageStatus.ACCEPTED in package.status:
            raise BadRequestError("Cannot withdraw an accepted package")

        if PackageStatus.WITHDRAWN in package.status:
            raise BadRequestError("Package has already been withdrawn")

    @classmethod
    def start_review(cls, package_id, _session=None):
        """Start the review process for the package."""
        package = cls._get_and_validate_package_for_starting_review(package_id)

        if _session is None:
            with session_scope() as session:
                cls.start_review_process(package, package_id, session)
        else:
            cls.start_review_process(package, package_id, _session)

        return package

    @classmethod
    def start_review_process(cls, package, package_id, session):
        """Common logic for starting the review process."""
        review_item = cls._get_review_item(package)
        if not review_item:
            current_app.logger.info(f"Review form not found in package {package_id}")
            raise BadRequestError("Review form not found in package")
        if review_item.status != ItemStatus.SUBMITTED:
            current_app.logger.info(f"Review form in package {package_id} is not submitted")
            return
        item_data = {
            'status': ItemStatus.UNDER_REVIEW.value,
            'review_start_date': datetime.now(UTC).isoformat()
        }
        cls._update_review_item(review_item, item_data, session)
        cls._update_package_status(package_id, session, package)
        new_metadata = {
            PackageMetadataFields.REVIEW_START_DATE.value: item_data.get('review_start_date')
        }
        cls._update_package_metadata(session, package_id, new_metadata)
        cls._log_activity_start_review(package, session)

    @staticmethod
    def _get_review_item(package):
        """Get the review item from the package."""
        if package.type.name == PackageTypeEnum.IEM.value:
            return next((item for item in package.items
                         if item.type.name == SubmissionItemType.IEM.value), None)
        if package.type.name == PackageTypeEnum.MANAGEMENT_PLAN.value:
            return next((item for item in package.items
                         if item.type.name == SubmissionItemType.MANAGEMENT_PLAN_FORM.value), None)
        raise BadRequestError("Unsupported package type")

    @staticmethod
    def _log_activity_start_review(package, session):
        """Log activity for starting management plan review."""
        review_action_map = {
            PackageTypeEnum.IEM.value: ActivityActionType.START_IEM_REVIEW.value,
            PackageTypeEnum.MANAGEMENT_PLAN.value: ActivityActionType.START_MP_REVIEW.value
        }
        action = review_action_map.get(package.type.name)
        if not action:
            raise BadRequestError("Unsupported package type for review")
        ActivityLogService.log_activity(
            entity_id=package.version.original_package_id if package.version else package.id,
            action=action,
            entity_version=package.version.version if package.version else 1,
            session=session
        )

    @classmethod
    def start_cr_check(cls, package_id):
        """Start the consultation check process for the package."""
        package = cls._get_and_validate_package_for_starting_review(package_id)
        item_data = {
            'status': ItemStatus.UNDER_CONSULTATION_CHECK.value,
            'review_start_date': datetime.now(UTC).isoformat()
        }
        with session_scope() as session:
            cls._update_cr_status(
                package.items, item_data, session)
            cls._update_package_status(package_id, session, package)
            new_metadata = {
                PackageMetadataFields.CONSULTATION_CHECK_START_DATE.value: item_data.get('review_start_date')
            }
            cls._update_package_metadata(session, package_id, new_metadata)
            cls._log_activity_start_consultation_check(package, session)
            session.flush()
            session.commit()
            return package

    @staticmethod
    def _log_activity_start_consultation_check(package, session):
        """Log activity for starting consultation check."""
        ActivityLogService.log_activity(
            entity_id=package.version.original_package_id if package.version else package.id,
            action=ActivityActionType.START_CONSULTATION_CHECK.value,
            entity_version=package.version.version if package.version else 1,
            session=session
        )

    @staticmethod
    def _unsupported_status(*args, **kwargs):
        """Handle unsupported status."""
        raise BadRequestError("Status is not supported.")

    @staticmethod
    def _create_email_queue_record(package, session):
        """Create email queue records for proponent and staff."""
        current_app.logger.info(f"Creating email queue records for package {package.id}")
        SubmitEmailQueueService.queue_package_submission_emails(package, session=session)
        current_app.logger.info(f"Email queue records created for package {package.id}")

    @classmethod
    def _get_state_updater(cls, status) -> callable:
        """Retrieve the appropriate state updater function based on status."""
        state_updaters = defaultdict(
            lambda: cls._unsupported_status,
            {
                PackageStatus.SUBMITTED.value: cls.submit_package,
                PackageStatus.UNDER_REVIEW.value: cls.start_review,
                PackageStatus.UNDER_CONSULTATION_CHECK.value: cls.start_cr_check,
                PackageStatus.ACKNOWLEDGED.value: cls.acknowledge_package,
                PackageStatus.APPROVED.value: cls.approve_package,
            }
        )
        return state_updaters[status]

    @classmethod
    def update_package_state(cls, package_id, request_data):
        """Update the state of the package based on the provided status."""
        status = request_data.get("status")
        state_updater = cls._get_state_updater(status)
        return state_updater(package_id)

    @classmethod
    def create_update_request(cls, package_id, request_data):
        """Create an update request for the package."""
        package = cls._get_and_validate_package_for_update_request(package_id)

        # Validate GIS role if update request is for GIS documents
        cls._validate_gis_role_for_update_request(package, request_data)

        cls._create_update_request(package, request_data)
        cls._log_activity_update_request(package)
        cls._update_request_creation_email_queue(package.id)
        return package

    @classmethod
    def _create_update_request(cls, package, request_data):
        """Create an update request for the package."""
        update_request = UpdateRequestModel(
            submission_package_id=package.id,
            submission_item_types=request_data.get("submission_item_types"),
            reason=request_data.get("reason"),
            created_by=TokenInfo.get_username()
        )
        update_request.save()
        return update_request

    @classmethod
    def _update_request_creation_email_queue(cls, package_id):
        """Create an email queue record for an update request."""
        SubmitEmailQueueService.queue_package_email(
            package_id,
            MANAGEMENT_PLAN_UPDATE_REQUEST_CREATED_EMAIL_TEMPLATE,
        )

    @staticmethod
    def _log_activity_update_request(package):
        """Log activity for update request creation."""
        ActivityLogService.log_activity(
            entity_id=package.version.original_package_id if package.version else package.id,
            action=ActivityActionType.UPDATE_REQUESTED.value,
            entity_version=package.version.version if package.version else 1,
        )

    @classmethod
    def _get_and_validate_package_for_update_request(cls, package_id):
        """Validate package status for update request."""
        package = cls.get_package_by_id(package_id)
        if not package:
            raise ResourceNotFoundError("Package not found")
        if not package.submitted_on:
            raise BadRequestError(
                "Cannot create an update request for a package that has not been submitted")
        if PackageStatus.APPROVED in package.status:
            raise BadRequestError(
                "Cannot create an update request for a package that has been approved")
        if PackageStatus.ACCEPTED in package.status:
            raise BadRequestError(
                "Cannot create an update request for a package that has been accepted")
        if PackageStatus.REJECTED in package.status:
            raise BadRequestError(
                "Cannot create an update request for a package that has been rejected")
        if PackageStatus.NOT_APPROVED in package.status:
            raise BadRequestError(
                "Cannot create an update request for a package that has not been approved")
        return package

    @classmethod
    def _get_and_validate_package_for_starting_review(cls, package_id):
        """Validate package status for update request."""
        package = cls.get_package_by_id(package_id)
        if not package:
            raise ResourceNotFoundError("Package not found")
        if package.completed_on:
            raise BadRequestError(
                "Cannot create a review for a package that has been completed")
        if PackageStatus.REJECTED.value in package.status:
            raise BadRequestError(
                "Cannot create a review for a package that has been rejected")
        return package

    @classmethod
    def _validate_gis_role_for_update_request(cls, package, request_data):
        """Validate GIS role if update request is for GIS documents."""
        submission_item_types = request_data.get("submission_item_types", [])

        # Check if any of the submission items contain GIS documents
        is_gis_update_request = cls._is_gis_update_request(package, submission_item_types)

        if is_gis_update_request:
            # For GIS documents, user must have GIS extended edit role or full access
            if not has_gis_extended_edit_role():
                raise BadRequestError("GIS extended edit role required for GIS document update requests")

    @classmethod
    def _is_gis_update_request(cls, package, submission_item_types):
        """Check if update request is for GIS documents.

        GIS documents are identified by item type name 'Geospatial Information'.
        """
        # Get all items for the specified item types
        for item in package.items:
            if item.type_id in submission_item_types:
                # Check if this item type is Geospatial Information
                if item.type and item.type.name == GIS_ITEM_TYPE_NAME:
                    return True
        return False

    @classmethod
    def _validate_gis_role_for_existing_update_request(cls, package, update_request):
        """Validate GIS role for existing update request (accept/withdraw operations)."""
        # Check if the update request is for GIS documents
        is_gis_update_request = cls._is_gis_update_request(package, update_request.submission_item_types)

        if is_gis_update_request:
            # For GIS documents, user must have GIS extended edit role or full access
            if not has_gis_extended_edit_role():
                raise BadRequestError("GIS extended edit role required for GIS document update requests")

    @classmethod
    def create_update_request_note(cls, package_id, update_request_id, request_data):
        """Create a note for an update request."""
        authorization.has_access_to_package(package_id)
        update_request = UpdateRequestModel.find_by_id(update_request_id)
        cls._validate_create_update_request_note(package_id, update_request)
        auth_guid = TokenInfo.get_username()
        update_request.note = request_data.get("note")
        update_request.note_updated_by = auth_guid
        update_request.note_updated_at = datetime.now(UTC)
        update_request.save()
        package = cls.get_package_by_id(package_id)
        return package

    @classmethod
    def update_update_request_note(cls, package_id, update_request_id, request_data):
        """Update an existing note for an update request."""
        authorization.has_access_to_package(package_id)
        update_request = UpdateRequestModel.find_by_id(update_request_id)
        cls._validate_update_update_request_note(package_id, update_request)
        auth_guid = TokenInfo.get_username()
        update_request.note = request_data.get("note")
        update_request.note_updated_by = auth_guid
        update_request.note_updated_at = datetime.now(UTC)
        update_request.save()
        package = cls.get_package_by_id(package_id)
        return package

    @classmethod
    def _validate_account_user(cls):
        """Validate the account user."""
        auth_guid = TokenInfo.get_username()
        user = User.get_by_guid(auth_guid)
        if not user or not user.type == UserType.PROPONENT:
            raise BadRequestError("User is not an account user")

    @classmethod
    def _validate_create_update_request_note(cls, package_id, update_request):
        """Validate the creation of an update request note."""
        if not update_request:
            raise ResourceNotFoundError("Update request not found")
        if update_request.submission_package_id != package_id:
            raise BadRequestError("Update request does not belong to the specified package")
        if update_request.note:
            raise BadRequestError("Note already exists for the update request")
        if not update_request.active:
            raise BadRequestError("Update request is not active")

    @classmethod
    def _validate_no_empty_submissions(cls, package):
        """Validate that there are no empty submissions when resubmitting an acknowledged package."""
        empty_submissions = []

        for item in package.items:
            for submission in item.submissions:
                # Check if submission is empty (no document and no form)
                if not submission.submitted_document_id and not submission.submitted_form_id:
                    empty_submissions.append({
                        'item_type': item.type.name,
                        'submission_id': submission.id
                    })

        if empty_submissions:
            item_types = ', '.join(set(s['item_type'] for s in empty_submissions))
            raise BadRequestError(
                f"Cannot resubmit an acknowledged package with empty submissions. "
                f"Please add documents or forms to the following sections: {item_types}"
            )

    @classmethod
    def _validate_update_update_request_note(cls, package_id, update_request):
        """Validate the update of an update request note."""
        if not update_request:
            raise ResourceNotFoundError("Update request not found")
        if update_request.submission_package_id != package_id:
            raise BadRequestError("Update request does not belong to the specified package")
        if not update_request.note:
            raise BadRequestError("No note exists to update")
        if not update_request.active:
            raise BadRequestError("Update request is not active")
        if update_request.status != UpdateRequestStatus.OPEN.value:
            raise BadRequestError("Cannot edit note after package resubmission")
        cls._validate_account_user()
