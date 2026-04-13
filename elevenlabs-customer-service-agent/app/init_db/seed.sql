-- Synthetic data for local/demo. Run after create_tables.sql (see docs/database.md).
-- Uses provider_names / general_statuses rows inserted in create_tables.sql (resolved by name).
-- Demo times: wall clock interpreted as UTC (see docs/database.md).
-- psql: psql "$DATABASE_URL" -f app/init_db/seed.sql

INSERT INTO customers (id, phone, email, name, plan, status)
VALUES
    ('11111111-0001-4000-8000-000000000001', '+15551234001', 'jane.doe@example.com', 'Jane Doe', 'premium', 'active'),
    ('11111111-0002-4000-8000-000000000002', '+15551234002', 'john.smith@example.com', 'John Smith', 'standard', 'active'),
    ('11111111-0003-4000-8000-000000000003', '+15551234003', 'alice.jones@example.com', 'Alice Jones', 'standard', 'active'),
    ('11111111-0004-4000-8000-000000000004', '+15551234004', 'bob.wilson@example.com', 'Bob Wilson', 'premium', 'suspended'),
    ('11111111-0005-4000-8000-000000000005', '+15551234005', 'carol.brown@example.com', 'Carol Brown', 'standard', 'active')
ON CONFLICT (id) DO NOTHING;

---- SPLIT ----

INSERT INTO providers (id, kind, name, active)
VALUES
    (
        'aaaaaaaa-0001-4000-8000-000000000001',
        (SELECT id FROM provider_names WHERE name = 'Doctor' LIMIT 1),
        'Dr. Sam Chen',
        true
    ),
    (
        'aaaaaaaa-0002-4000-8000-000000000001',
        (SELECT id FROM provider_names WHERE name = 'Nurse' LIMIT 1),
        'Alex Rivera, RN',
        true
    ),
    (
        'aaaaaaaa-0003-4000-8000-000000000001',
        (SELECT id FROM provider_names WHERE name = 'Room' LIMIT 1),
        'Exam Room 1',
        true
    ),
    (
        'aaaaaaaa-0003-4000-8000-000000000002',
        (SELECT id FROM provider_names WHERE name = 'Room' LIMIT 1),
        'Exam Room 2',
        true
    ),
    (
        'aaaaaaaa-0004-4000-8000-000000000001',
        (SELECT id FROM provider_names WHERE name = 'Equipment' LIMIT 1),
        'Ultrasound Unit A',
        true
    )
ON CONFLICT (id) DO NOTHING;

---- SPLIT ----

INSERT INTO callback_requests (id, customer_id, phone, requested_for, status)
VALUES
    (
        gen_random_uuid(),
        '11111111-0001-4000-8000-000000000001',
        '+15551234001',
        'next available',
        (SELECT id FROM general_statuses WHERE name = 'completed' LIMIT 1)
    ),
    (
        gen_random_uuid(),
        '11111111-0002-4000-8000-000000000002',
        '+15551234002',
        'tomorrow 2pm',
        (SELECT id FROM general_statuses WHERE name = 'pending' LIMIT 1)
    ),
    (
        gen_random_uuid(),
        '11111111-0003-4000-8000-000000000003',
        '+15551234003',
        'next available',
        (SELECT id FROM general_statuses WHERE name = 'pending' LIMIT 1)
    );

---- SPLIT ----

INSERT INTO appointments (id, customer_id, scheduled_at, subject, status, notes)
VALUES
    (
        'bbbbbbbb-0001-4000-8000-000000000001',
        '11111111-0001-4000-8000-000000000001',
        ((CURRENT_DATE + 2) + TIME '10:00:00') AT TIME ZONE 'UTC',
        'Annual check-in',
        (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1),
        '30 min'
    ),
    (
        'bbbbbbbb-0002-4000-8000-000000000002',
        '11111111-0002-4000-8000-000000000002',
        ((CURRENT_DATE + 5) + TIME '14:30:00') AT TIME ZONE 'UTC',
        'Follow-up visit',
        (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1),
        NULL
    ),
    (
        'bbbbbbbb-0003-4000-8000-000000000003',
        '11111111-0001-4000-8000-000000000001',
        ((CURRENT_DATE - 1) + TIME '11:00:00') AT TIME ZONE 'UTC',
        'Billing review',
        (SELECT id FROM general_statuses WHERE name = 'completed' LIMIT 1),
        'Resolved.'
    ),
    (
        'bbbbbbbb-0004-4000-8000-000000000004',
        '11111111-0003-4000-8000-000000000003',
        ((CURRENT_DATE + 7) + TIME '09:00:00') AT TIME ZONE 'UTC',
        'New patient intake',
        (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1),
        NULL
    ),
    (
        'bbbbbbbb-0005-4000-8000-000000000005',
        '11111111-0004-4000-8000-000000000004',
        ((CURRENT_DATE - 3) + TIME '15:00:00') AT TIME ZONE 'UTC',
        'Account review',
        (SELECT id FROM general_statuses WHERE name = 'cancelled' LIMIT 1),
        'Customer rescheduled'
    )
ON CONFLICT (id) DO NOTHING;

---- SPLIT ----

INSERT INTO appointment_resource_bookings
    (id, appointment_id, provider_id, booking_date, slot_template_id, status)
VALUES
    (gen_random_uuid(), 'bbbbbbbb-0001-4000-8000-000000000001', 'aaaaaaaa-0001-4000-8000-000000000001', CURRENT_DATE + 2, 3, (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0001-4000-8000-000000000001', 'aaaaaaaa-0003-4000-8000-000000000001', CURRENT_DATE + 2, 3, (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0002-4000-8000-000000000002', 'aaaaaaaa-0001-4000-8000-000000000001', CURRENT_DATE + 5, 8, (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0002-4000-8000-000000000002', 'aaaaaaaa-0003-4000-8000-000000000001', CURRENT_DATE + 5, 8, (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0003-4000-8000-000000000003', 'aaaaaaaa-0001-4000-8000-000000000001', CURRENT_DATE - 1, 5, (SELECT id FROM general_statuses WHERE name = 'completed' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0003-4000-8000-000000000003', 'aaaaaaaa-0003-4000-8000-000000000001', CURRENT_DATE - 1, 5, (SELECT id FROM general_statuses WHERE name = 'completed' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0004-4000-8000-000000000004', 'aaaaaaaa-0001-4000-8000-000000000001', CURRENT_DATE + 7, 1, (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0004-4000-8000-000000000004', 'aaaaaaaa-0003-4000-8000-000000000001', CURRENT_DATE + 7, 1, (SELECT id FROM general_statuses WHERE name = 'scheduled' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0005-4000-8000-000000000005', 'aaaaaaaa-0001-4000-8000-000000000001', CURRENT_DATE - 3, 9, (SELECT id FROM general_statuses WHERE name = 'cancelled' LIMIT 1)),
    (gen_random_uuid(), 'bbbbbbbb-0005-4000-8000-000000000005', 'aaaaaaaa-0003-4000-8000-000000000001', CURRENT_DATE - 3, 9, (SELECT id FROM general_statuses WHERE name = 'cancelled' LIMIT 1))
ON CONFLICT (provider_id, booking_date, slot_template_id) DO NOTHING;

---- SPLIT ----

-- Demo inventory: NDC values must exist in rxnorm_attributes (RXNSAT) for lookups to work.
-- In RxNorm RRF loads, NDC is stored in ATV — usually as an 11-character digit string (no dashes);
-- see docs/RAG_RXNORM.md. Static made-up NDCs will not appear in RXNSAT.
-- This block samples up to 100 distinct ATV values from your loaded RXNSAT (non-suppressed rows).
-- Run AFTER RxNorm RXNSAT data is ingested into rxnorm_attributes; otherwise inserts 0 rows.
-- Replace drug_name labels with your formulary text as needed.
INSERT INTO inventory (drug_name, ndc)
SELECT 'Clinic formulary item ' || LPAD(seq::text, 3, '0'), atv
FROM (
    SELECT atv, ROW_NUMBER() OVER (ORDER BY atv) AS seq
    FROM (
        SELECT DISTINCT atv
        FROM rxnorm_attributes
        WHERE atn = 'NDC'
          AND (suppress IS NULL OR suppress = 'N')
          AND atv IS NOT NULL
          AND btrim(atv) <> ''
    ) AS distinct_ndc
    LIMIT 100
) AS picked
WHERE NOT EXISTS (SELECT 1 FROM inventory)
  AND EXISTS (SELECT 1 FROM rxnorm_attributes WHERE atn = 'NDC' LIMIT 1);
