# EPIC.submit Production Smoke Test Seed

This runbook is for controlled production smoke testing after an EPIC.submit release.

These scripts create synthetic release-test data only. They are not application migrations, and they should not be wired into app startup, deploy jobs, or automated seed jobs.

Use this only with approved production testing access. The scripts intentionally use plain `insert` statements and no safety checks. If they need to be rerun, run the teardown first.

## Test Data

Synthetic proponent:

```text
ZZZ EPIC.submit Smoke Test Proponent
```

Synthetic projects:

```text
ZZZ Smoke - MPT/IEM Project - DO NOT USE
ZZZ Smoke - IPD/Additional Info Project - DO NOT USE
```

The `ZZZ` prefix is intentional so the records are easy to search and clearly not real project data.

## Submission Type Coverage

### Management Plan

Management Plan testing uses the Conditions-backed smoke project:

```text
ZZZ Smoke - MPT/IEM Project - DO NOT USE
```

This project has:

- a Submit project with `has_approved_condition = true`
- a matching Conditions project
- one approved Management Plan condition
- one approved Management Plan named `ZZZ Smoke Management Plan`

Use the UI for the rest of the flow:

1. Invite/onboard the synthetic proponent from the staff UI.
2. Log in as the test proponent.
3. Open the MPT/IEM smoke project.
4. Create a Management Plan package.
5. Upload a small test document.
6. Submit the package.
7. Verify package status, file download, staff visibility, and email queue entries.

### IEM

IEM testing also uses the Conditions-backed smoke project:

```text
ZZZ Smoke - MPT/IEM Project - DO NOT USE
```

The Conditions seed includes one IEM condition with:

```text
Independent Environmental Monitor Terms of Engagement
```

Note: IEM visibility depends on the deployed Submit code exposing condition-backed IEM package creation. If IEM does not show up in the UI, that is a product/code behavior to verify separately. The seed data includes the required Conditions-side IEM data.

### Initial Project Description

IPD testing uses the work-backed smoke project:

```text
ZZZ Smoke - IPD/Additional Info Project - DO NOT USE
```

This project has one synthetic `track_works` row in an enabled Early Engagement / Assessment phase. During onboarding, Submit should create the default Initial Project Description & Engagement Plan package when this work is selected.

Use the UI for the rest of the flow:

1. Invite/onboard the synthetic proponent from the staff UI.
2. Select the IPD/Additional Info smoke project work during onboarding.
3. Log in as the test proponent.
4. Open the default Initial Project Description & Engagement Plan package.
5. Upload a small test document.
6. Submit the package.
7. Verify package status, file download, staff visibility, and email queue entries.

### Additional Information

Additional Information testing uses the same work-backed smoke project:

```text
ZZZ Smoke - IPD/Additional Info Project - DO NOT USE
```

Use the UI for the rest of the flow:

1. Log in as the test proponent.
2. Open the IPD/Additional Info smoke project.
3. Create an Additional Information submission.
4. Upload a small test document.
5. Submit the package.
6. Verify package status, file download, staff visibility, and email queue entries.

## Submit DB Seed

Run this in the EPIC.submit database.

```sql
begin;

insert into proponents (
  id, name, status, is_deleted,
  created_date, updated_date, created_by, updated_by
)
values (
  999900001,
  'ZZZ EPIC.submit Smoke Test Proponent',
  'ELIGIBLE',
  false,
  now(),
  now(),
  'prod-smoke-seed',
  'prod-smoke-seed'
);

insert into projects (
  name, proponent_id, ea_certificate, epic_guid, has_approved_condition
)
values (
  'ZZZ Smoke - MPT/IEM Project - DO NOT USE',
  999900001,
  'ZZZ-SMOKE-EAC',
  'ZZZ-SUBMIT-SMOKE-CONDITIONS',
  true
);

insert into projects (
  name, proponent_id, ea_certificate, epic_guid, has_approved_condition
)
values (
  'ZZZ Smoke - IPD/Additional Info Project - DO NOT USE',
  999900001,
  null,
  'ZZZ-SUBMIT-SMOKE-WORK',
  false
);

insert into track_works (
  id, project_id, current_phase_id, work_state, title, contact_email,
  is_active, is_deleted, created_date, updated_date, created_by, updated_by
)
select
  999900002,
  p.id,
  tp.id,
  'IN_PROGRESS',
  'ZZZ Smoke IPD / Additional Info Work',
  'EAO.ManagementPlanSupport@gov.bc.ca',
  true,
  false,
  now(),
  now(),
  'prod-smoke-seed',
  'prod-smoke-seed'
from projects p
join track_phases tp
  on tp.name = 'Early Engagement'
 and tp.work_type_name = 'Assessment'
 and tp.enable_submit = true
 and tp.is_active = true
 and tp.is_deleted = false
where p.epic_guid = 'ZZZ-SUBMIT-SMOKE-WORK'
limit 1;

commit;
```

## Conditions DB Seed

Run this in the EPIC.conditions database.

```sql
begin;

insert into condition.projects (
  project_id, project_name, project_type, is_active,
  created_date, updated_date, created_by, updated_by
)
values (
  'ZZZ-SUBMIT-SMOKE-CONDITIONS',
  'ZZZ Smoke - MPT/IEM Project - DO NOT USE',
  'Smoke Test',
  true,
  now(),
  now(),
  'prod-smoke-seed',
  'prod-smoke-seed'
);

insert into condition.documents (
  document_id, document_type_id, document_category_id, document_label, document_file_name,
  date_issued, act, first_nations, consultation_records_required,
  is_latest_amendment_added, is_active, project_id,
  created_date, updated_date, created_by, updated_by
)
select
  'ZZZ-SUBMIT-SMOKE-CERT',
  dt.id,
  dc.id,
  'ZZZ Smoke Certificate',
  'zzz-smoke-certificate.pdf',
  current_date,
  2018,
  array[]::text[],
  false,
  false,
  true,
  'ZZZ-SUBMIT-SMOKE-CONDITIONS',
  now(),
  now(),
  'prod-smoke-seed',
  'prod-smoke-seed'
from condition.document_types dt
cross join condition.document_categories dc
where dt.document_type = 'Certificate'
  and dc.category_name = 'Certificate and Amendments'
limit 1;

with mp_condition as (
  insert into condition.conditions (
    project_id, document_id, condition_name, condition_number, condition_text,
    topic_tags, subtopic_tags, effective_from,
    is_approved, is_topic_tags_approved, is_condition_attributes_approved,
    is_active, is_standard_condition, requires_management_plan, condition_type,
    created_date, updated_date, created_by, updated_by
  )
  values (
    'ZZZ-SUBMIT-SMOKE-CONDITIONS',
    'ZZZ-SUBMIT-SMOKE-CERT',
    'ZZZ Smoke Management Plan Condition',
    9001,
    'Submit the ZZZ Smoke Management Plan to EAO for approval before construction.',
    array['Smoke Test']::text[],
    array[]::text[],
    now(),
    true,
    true,
    true,
    true,
    false,
    true,
    'ADD',
    now(),
    now(),
    'prod-smoke-seed',
    'prod-smoke-seed'
  )
  returning id
),
mp_plan as (
  insert into condition.management_plans (
    condition_id, name, is_approved,
    created_date, updated_date, created_by, updated_by
  )
  select
    id,
    'ZZZ Smoke Management Plan',
    true,
    now(),
    now(),
    'prod-smoke-seed',
    'prod-smoke-seed'
  from mp_condition
  returning id, condition_id
)
insert into condition.condition_attributes (
  condition_id, management_plan_id, attribute_key_id, attribute_value,
  created_date, updated_date, created_by, updated_by
)
select
  mp_plan.condition_id,
  mp_plan.id,
  ak.id,
  v.attribute_value,
  now(),
  now(),
  'prod-smoke-seed',
  'prod-smoke-seed'
from mp_plan
join (
  values
    ('submitted_to_eao_for', 'Approval'),
    ('milestones_related_to_plan_submission', '{"Before construction"}'),
    ('milestones_related_to_plan_implementation', '{"Construction"}'),
    ('time_associated_with_submission_milestone', '30 days before construction'),
    ('requires_consultation', 'true'),
    ('parties_required_to_be_consulted', '{"EAO"}')
) as v(external_key, attribute_value) on true
join condition.attribute_keys ak on ak.external_key = v.external_key;

with iem_condition as (
  insert into condition.conditions (
    project_id, document_id, condition_name, condition_number, condition_text,
    topic_tags, subtopic_tags, effective_from,
    is_approved, is_topic_tags_approved, is_condition_attributes_approved,
    is_active, is_standard_condition, requires_management_plan, condition_type,
    created_date, updated_date, created_by, updated_by
  )
  values (
    'ZZZ-SUBMIT-SMOKE-CONDITIONS',
    'ZZZ-SUBMIT-SMOKE-CERT',
    'ZZZ Smoke IEM Condition',
    9002,
    'Submit Independent Environmental Monitor Terms of Engagement to EAO for review.',
    array['Smoke Test']::text[],
    array[]::text[],
    now(),
    true,
    true,
    true,
    true,
    false,
    false,
    'ADD',
    now(),
    now(),
    'prod-smoke-seed',
    'prod-smoke-seed'
  )
  returning id
)
insert into condition.condition_attributes (
  condition_id, management_plan_id, attribute_key_id, attribute_value,
  created_date, updated_date, created_by, updated_by
)
select
  iem_condition.id,
  null,
  ak.id,
  v.attribute_value,
  now(),
  now(),
  'prod-smoke-seed',
  'prod-smoke-seed'
from iem_condition
join (
  values
    ('requires_iem_terms_of_engagement', 'true'),
    ('deliverable_name', 'Independent Environmental Monitor Terms of Engagement'),
    ('submitted_to_eao_for', 'Review'),
    ('milestones_related_to_plan_submission', '{"Before construction"}'),
    ('milestones_related_to_plan_implementation', '{"Construction"}'),
    ('time_associated_with_submission_milestone', '30 days before construction'),
    ('requires_consultation', 'false')
) as v(external_key, attribute_value) on true
join condition.attribute_keys ak on ak.external_key = v.external_key;

commit;
```

## Smoke Test Checks

Use these checks after running the UI smoke test.

### Email Queue

```sql
select id, entity_type, entity_id, template_name, status, sent_at, error_message, payload
from email_queue
where created_at >= now() - interval '1 day'
  and (
    payload::text like '%ZZZ Smoke%'
    or payload::text like '%ZZZ EPIC.submit%'
  )
order by id desc;
```

### Smoke Packages

```sql
select p.id, p.name, pt.name as package_type, p.status, p.submitted_on, p.created_date
from packages p
join package_types pt on pt.id = p.type_id
join account_projects ap on ap.id = p.account_project_id
join projects pr on pr.id = ap.project_id
where pr.epic_guid in (
  'ZZZ-SUBMIT-SMOKE-CONDITIONS',
  'ZZZ-SUBMIT-SMOKE-WORK'
)
order by p.id desc;
```

## Submit DB Teardown

Run this in the EPIC.submit database after smoke testing is complete.

This removes the synthetic proponent, projects, work, account/project associations, packages, submissions, forms, submitted document rows, and email queue rows created for this smoke test.

It does not delete the actual uploaded files from object storage.

```sql
begin;

create temp table smoke_project_ids on commit drop as
select id
from projects
where epic_guid in (
  'ZZZ-SUBMIT-SMOKE-CONDITIONS',
  'ZZZ-SUBMIT-SMOKE-WORK'
);

create temp table smoke_account_ids on commit drop as
select id
from accounts
where proponent_id = 999900001;

create temp table smoke_invitation_ids on commit drop as
select id
from invitations
where account_id in (select id from smoke_account_ids);

create temp table smoke_package_ids on commit drop as
select p.id
from packages p
join account_projects ap on ap.id = p.account_project_id
where ap.project_id in (select id from smoke_project_ids);

create temp table smoke_submitted_documents on commit drop as
select distinct s.submitted_document_id as id
from submissions s
join items i on i.id = s.item_id
where i.package_id in (select id from smoke_package_ids)
  and s.submitted_document_id is not null;

create temp table smoke_submitted_forms on commit drop as
select distinct s.submitted_form_id as id
from submissions s
join items i on i.id = s.item_id
where i.package_id in (select id from smoke_package_ids)
  and s.submitted_form_id is not null;

delete from email_queue
where (entity_type = 'PACKAGE' and entity_id in (select id from smoke_package_ids))
   or (entity_type = 'INVITATION' and entity_id in (select id from smoke_invitation_ids));

delete from submissions
where item_id in (
  select id from items
  where package_id in (select id from smoke_package_ids)
);

delete from submitted_documents
where id in (select id from smoke_submitted_documents);

delete from submitted_forms
where id in (select id from smoke_submitted_forms);

delete from packages
where id in (select id from smoke_package_ids);

delete from package_versions
where original_package_id in (select id from smoke_package_ids);

delete from accounts
where id in (select id from smoke_account_ids);

delete from track_works
where id = 999900002
   or project_id in (select id from smoke_project_ids);

delete from projects
where id in (select id from smoke_project_ids);

delete from proponents
where id = 999900001;

commit;
```

## Conditions DB Teardown

Run this in the EPIC.conditions database after smoke testing is complete.

```sql
begin;

delete from condition.condition_attributes
where condition_id in (
  select id
  from condition.conditions
  where project_id = 'ZZZ-SUBMIT-SMOKE-CONDITIONS'
);

delete from condition.management_plans
where condition_id in (
  select id
  from condition.conditions
  where project_id = 'ZZZ-SUBMIT-SMOKE-CONDITIONS'
);

delete from condition.conditions
where project_id = 'ZZZ-SUBMIT-SMOKE-CONDITIONS';

delete from condition.documents
where project_id = 'ZZZ-SUBMIT-SMOKE-CONDITIONS';

delete from condition.projects
where project_id = 'ZZZ-SUBMIT-SMOKE-CONDITIONS';

commit;
```
