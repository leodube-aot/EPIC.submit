"""Test submission item review creation."""

from http import HTTPStatus

from faker import Faker

from submit_api.enums.item_status import ItemStatus
from submit_api.enums.package_type import PackageTypeId
from submit_api.models.item_type import SubmissionItemTypeId
from submit_api.models.submission_review import SubmissionReviewStatus
from submit_api.models.submission_review_entry import SubmissionReviewEntryType
from submit_api.schemas.submission_review import SubmissionReviewSchema
from tests.utilities.factory_scenarios import TestJwtClaims
from tests.utilities.factory_utils import create_contact_info_submission
from tests.utilities.factory_utils import factory_auth_header
from tests.utilities.factory_utils import factory_item_model
from tests.utilities.factory_utils import factory_package_model
from tests.utilities.factory_utils import factory_user_model
from tests.utilities.factory_utils import set_global_token_info


fake = Faker()

ITEMS_URL = "/api/items"


def test_create_review_consultation_record_success(client, session, jwt):
    """Test creating a review for a submission item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.MANAGEMENT_PLAN.value)
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    cr_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                                 status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)

    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "question_1": "Answer 1",
            "question_2": "Answer 2"
        },
        "status": SubmissionReviewStatus.APPROVED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to create a review
    response = client.post(
        f"{ITEMS_URL}/{cr_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == cr_item.id

    mp_item = next(
        item for item in package.items if item.type_id == SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value
    )
    # Validate that the management plan item status is updated to UNDER_REVIEW
    assert mp_item.status == ItemStatus.UNDER_REVIEW


def test_create_review_consultation_record_fail(client, session, jwt):
    """Test creating a review for a submission item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.MANAGEMENT_PLAN.value)
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    cr_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                                 status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)

    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "passedConsultationCheck": "NO",
            "reason": fake.paragraph(),
            "submission_item_types": [SubmissionItemTypeId.CONSULTATION_RECORD.value]
        },
        "status": SubmissionReviewStatus.REJECTED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to create a review
    response = client.post(
        f"{ITEMS_URL}/{cr_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == cr_item.id
    assert len(package.update_requests) == 1


def test_approve_management_plan_item_satisfaction(client, session, jwt):
    """Test approving a management plan item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.MANAGEMENT_PLAN.value,
                                    submitted_to_eao_for='Satisfaction')
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    mp_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value,
                                 status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)

    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "question_1": "Answer 1",
            "question_2": "Answer 2"
        },
        "status": SubmissionReviewStatus.APPROVED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to approve the management plan item
    response = client.post(
        f"{ITEMS_URL}/{mp_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == mp_item.id

    # Validate that the management plan item status is updated to APPROVED
    assert mp_item.status == ItemStatus.SATISFIED
    assert package.completed_on is not None


def test_approve_management_plan_item_acceptance(client, session, jwt):
    """Test approving a management plan item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.MANAGEMENT_PLAN.value,
                                    submitted_to_eao_for='Acceptance')
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    mp_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value,
                                 status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)

    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "question_1": "Answer 1",
            "question_2": "Answer 2"
        },
        "status": SubmissionReviewStatus.APPROVED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to approve the management plan item
    response = client.post(
        f"{ITEMS_URL}/{mp_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == mp_item.id

    # Validate that the management plan item status is updated to APPROVED
    assert mp_item.status == ItemStatus.ACCEPTED
    assert package.completed_on is not None


def test_approve_management_plan_item_approval(client, session, jwt):
    """Test approving a management plan item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.MANAGEMENT_PLAN.value,
                                    submitted_to_eao_for='Approval')
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    mp_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value,
                                 status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)

    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "question_1": "Answer 1",
            "question_2": "Answer 2"
        },
        "status": SubmissionReviewStatus.APPROVED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to approve the management plan item
    response = client.post(
        f"{ITEMS_URL}/{mp_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == mp_item.id

    # Validate that the management plan item status is updated to APPROVED
    assert mp_item.status == ItemStatus.APPROVED
    assert package.completed_on is not None


def test_review_iem_package(client, session, jwt):
    """Test reviewing an IEM package."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.IEM.value, submitted_to_eao_for='Approval')
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    iem_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.IEM.value,
                                  status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)

    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "question_1": "Answer 1",
            "question_2": "Answer 2"
        },
        "status": SubmissionReviewStatus.APPROVED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to review the IEM package
    response = client.post(
        f"{ITEMS_URL}/{iem_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == iem_item.id

    # Validate that the IEM item status is updated to APPROVED
    assert iem_item.status == ItemStatus.APPROVED


def test_fail_management_plan_item(client, session, jwt):
    """Test approving a management plan item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.MANAGEMENT_PLAN.value,
                                    submitted_to_eao_for='Satisfaction')
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    contact_info_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONTACT_INFORMATION.value,
                                           status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    mp_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value,
                                 status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    create_contact_info_submission(item_id=contact_info_item.id, auth_guid=auth_guid)
    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "passed": "NO",
            "reason": fake.paragraph(),
            "submission_item_types": [SubmissionItemTypeId.MANAGEMENT_PLAN_FORM.value]
        },
        "status": SubmissionReviewStatus.REJECTED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to reject the management plan item
    response = client.post(
        f"{ITEMS_URL}/{mp_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == mp_item.id
    versions_response = client.get(
        f"/api/packages/{package.version.original_package_id}/versions",
        json=payload,
        headers=headers,
    )

    versions = versions_response.get_json()

    assert versions_response.status_code == HTTPStatus.OK
    assert len(versions) == 2


def test_fail_iem_item(client, session, jwt):
    """Test approving a management plan item."""
    claims = TestJwtClaims.staff_admin_role
    auth_guid = claims["preferred_username"]
    set_global_token_info(claims)
    factory_user_model(auth_guid=auth_guid)
    package = factory_package_model(package_type_id=PackageTypeId.IEM.value,
                                    submitted_to_eao_for='Satisfaction')
    package.submitted_on = fake.date_time_this_year()
    session.add(package)
    session.flush()
    contact_info_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONTACT_INFORMATION.value,
                                           status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    factory_item_model(package=package, item_type_id=SubmissionItemTypeId.CONSULTATION_RECORD.value,
                       status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    iem_item = factory_item_model(package=package, item_type_id=SubmissionItemTypeId.IEM.value,
                                  status=ItemStatus.SUBMITTED.value, submitted_by=auth_guid)
    create_contact_info_submission(item_id=contact_info_item.id, auth_guid=auth_guid)
    session.flush()

    # Generate authentication headers
    headers = factory_auth_header(jwt=jwt, claims=claims)

    # Payload for the review
    payload = {
        "form_answers": {
            "passed": "NO",
            "reason": fake.paragraph(),
            "submission_item_types": [SubmissionItemTypeId.IEM.value]
        },
        "status": SubmissionReviewStatus.REJECTED.value,
        "type": SubmissionReviewEntryType.MANAGER_CONFIRMATION.value
    }

    # Make the POST request to reject the management plan item
    response = client.post(
        f"{ITEMS_URL}/{iem_item.id}/review",
        json=payload,
        headers=headers,
    )

    # Assertions
    assert response.status_code == HTTPStatus.OK
    data = response.get_json()

    # Validate response against SubmissionReviewSchema
    schema = SubmissionReviewSchema()
    deserialized_data = schema.load(data)

    review_form = next(
        (entry['entry'] for entry in deserialized_data['entries'] if entry['type'].value == payload['type']),
        None
    )
    assert review_form == payload["form_answers"]
    assert deserialized_data["status"].value == payload["status"]
    assert deserialized_data["item_id"] == iem_item.id
    versions_response = client.get(
        f"/api/packages/{package.version.original_package_id}/versions",
        json=payload,
        headers=headers,
    )

    versions = versions_response.get_json()

    assert versions_response.status_code == HTTPStatus.OK
    assert len(versions) == 2
