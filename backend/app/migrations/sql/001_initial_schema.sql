-- ============================================================================
-- 001_initial_schema.sql
-- Nursery Analytics Platform — full schema (RBAC + dimensions + facts)
-- ============================================================================

-- ─── RBAC & dashboard composition ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(50) UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS permissions (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id            SERIAL PRIMARY KEY,
    role_id       INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS dashboard_modules (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(60) UNIQUE NOT NULL,
    name        VARCHAR(120) NOT NULL,
    icon        VARCHAR(60),
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id          SERIAL PRIMARY KEY,
    module_id   INTEGER NOT NULL REFERENCES dashboard_modules(id) ON DELETE CASCADE,
    key         VARCHAR(80) UNIQUE NOT NULL,
    title       VARCHAR(150) NOT NULL,
    viz_type    VARCHAR(40) NOT NULL,
    description TEXT,
    span        INTEGER NOT NULL DEFAULT 4,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS role_widget_access (
    id         SERIAL PRIMARY KEY,
    role_id    INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    widget_id  INTEGER NOT NULL REFERENCES dashboard_widgets(id) ON DELETE CASCADE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    position   INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_role_widget UNIQUE (role_id, widget_id)
);

-- ─── Dimensions ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_site (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(150) NOT NULL,
    borough          VARCHAR(100) NOT NULL,
    postcode         VARCHAR(12) NOT NULL,
    capacity         INTEGER NOT NULL,
    opened_on        DATE,
    monthly_overhead NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_room (
    id             SERIAL PRIMARY KEY,
    site_id        INTEGER NOT NULL REFERENCES dim_site(id) ON DELETE CASCADE,
    name           VARCHAR(100) NOT NULL,
    room_type      VARCHAR(30) NOT NULL,
    capacity       INTEGER NOT NULL,
    required_ratio INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_parent (
    id         SERIAL PRIMARY KEY,
    site_id    INTEGER NOT NULL REFERENCES dim_site(id),
    first_name VARCHAR(80) NOT NULL,
    last_name  VARCHAR(80) NOT NULL,
    email      VARCHAR(255) NOT NULL,
    phone      VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS dim_child (
    id              SERIAL PRIMARY KEY,
    site_id         INTEGER NOT NULL REFERENCES dim_site(id),
    room_id         INTEGER REFERENCES dim_room(id),
    parent_id       INTEGER REFERENCES dim_parent(id),
    first_name      VARCHAR(80) NOT NULL,
    last_name       VARCHAR(80) NOT NULL,
    dob             DATE NOT NULL,
    gender          VARCHAR(20),
    enrollment_date DATE,
    status          VARCHAR(20) NOT NULL,
    funding_type    VARCHAR(40),
    monthly_fee     NUMERIC(10,2) NOT NULL DEFAULT 0,
    allergies       VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_staff (
    id                  SERIAL PRIMARY KEY,
    site_id             INTEGER NOT NULL REFERENCES dim_site(id),
    first_name          VARCHAR(80) NOT NULL,
    last_name           VARCHAR(80) NOT NULL,
    role_title          VARCHAR(80) NOT NULL,
    qualification_level INTEGER NOT NULL,
    dbs_status          VARCHAR(20) NOT NULL,
    dbs_expiry          DATE,
    contract_hours      NUMERIC(6,2) NOT NULL DEFAULT 37.5,
    hourly_rate         NUMERIC(8,2) NOT NULL DEFAULT 12.0,
    is_agency           BOOLEAN NOT NULL DEFAULT FALSE,
    employment_status   VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key   DATE PRIMARY KEY,
    year       INTEGER NOT NULL,
    quarter    INTEGER NOT NULL,
    month      INTEGER NOT NULL,
    month_name VARCHAR(12) NOT NULL,
    day        INTEGER NOT NULL,
    dow        INTEGER NOT NULL,
    dow_name   VARCHAR(12) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- users references dim_site / dim_child / dim_staff, so created after them
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    full_name       VARCHAR(150) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role_id         INTEGER NOT NULL REFERENCES roles(id),
    site_id         INTEGER REFERENCES dim_site(id),
    linked_child_id INTEGER REFERENCES dim_child(id),
    linked_staff_id INTEGER REFERENCES dim_staff(id),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Facts ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_attendance (
    id          SERIAL PRIMARY KEY,
    child_id    INTEGER NOT NULL REFERENCES dim_child(id),
    site_id     INTEGER NOT NULL REFERENCES dim_site(id),
    room_id     INTEGER REFERENCES dim_room(id),
    date        DATE NOT NULL,
    status      VARCHAR(20) NOT NULL,
    check_in    TIMESTAMP,
    check_out   TIMESTAMP,
    late_pickup BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_attendance_date ON fact_attendance(date);
CREATE INDEX IF NOT EXISTS ix_attendance_site ON fact_attendance(site_id);
CREATE INDEX IF NOT EXISTS ix_attendance_child ON fact_attendance(child_id);

CREATE TABLE IF NOT EXISTS fact_enrollment_event (
    id         SERIAL PRIMARY KEY,
    child_id   INTEGER NOT NULL REFERENCES dim_child(id),
    site_id    INTEGER NOT NULL REFERENCES dim_site(id),
    event_type VARCHAR(30) NOT NULL,
    event_date DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_enroll_date ON fact_enrollment_event(event_date);
CREATE INDEX IF NOT EXISTS ix_enroll_site ON fact_enrollment_event(site_id);

CREATE TABLE IF NOT EXISTS fact_invoice (
    id              SERIAL PRIMARY KEY,
    child_id        INTEGER NOT NULL REFERENCES dim_child(id),
    site_id         INTEGER NOT NULL REFERENCES dim_site(id),
    issue_date      DATE NOT NULL,
    due_date        DATE NOT NULL,
    period_month    DATE NOT NULL,
    amount          NUMERIC(10,2) NOT NULL,
    funding_amount  NUMERIC(10,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL,
    paid_date       DATE
);
CREATE INDEX IF NOT EXISTS ix_invoice_period ON fact_invoice(period_month);
CREATE INDEX IF NOT EXISTS ix_invoice_site ON fact_invoice(site_id);
CREATE INDEX IF NOT EXISTS ix_invoice_status ON fact_invoice(status);

CREATE TABLE IF NOT EXISTS fact_payment (
    id           SERIAL PRIMARY KEY,
    invoice_id   INTEGER NOT NULL REFERENCES fact_invoice(id),
    child_id     INTEGER NOT NULL REFERENCES dim_child(id),
    site_id      INTEGER NOT NULL REFERENCES dim_site(id),
    payment_date DATE NOT NULL,
    amount       NUMERIC(10,2) NOT NULL,
    method       VARCHAR(20) NOT NULL,
    success      BOOLEAN NOT NULL DEFAULT TRUE,
    is_refund    BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_payment_date ON fact_payment(payment_date);
CREATE INDEX IF NOT EXISTS ix_payment_site ON fact_payment(site_id);

CREATE TABLE IF NOT EXISTS fact_staff_shift (
    id              SERIAL PRIMARY KEY,
    staff_id        INTEGER NOT NULL REFERENCES dim_staff(id),
    site_id         INTEGER NOT NULL REFERENCES dim_site(id),
    room_id         INTEGER REFERENCES dim_room(id),
    date            DATE NOT NULL,
    hours_scheduled NUMERIC(5,2) NOT NULL DEFAULT 0,
    hours_worked    NUMERIC(5,2) NOT NULL DEFAULT 0,
    overtime_hours  NUMERIC(5,2) NOT NULL DEFAULT 0,
    absent          BOOLEAN NOT NULL DEFAULT FALSE,
    absence_reason  VARCHAR(40)
);
CREATE INDEX IF NOT EXISTS ix_shift_date ON fact_staff_shift(date);
CREATE INDEX IF NOT EXISTS ix_shift_site ON fact_staff_shift(site_id);
CREATE INDEX IF NOT EXISTS ix_shift_staff ON fact_staff_shift(staff_id);

CREATE TABLE IF NOT EXISTS fact_incident (
    id            SERIAL PRIMARY KEY,
    child_id      INTEGER REFERENCES dim_child(id),
    site_id       INTEGER NOT NULL REFERENCES dim_site(id),
    incident_type VARCHAR(30) NOT NULL,
    severity      VARCHAR(20) NOT NULL,
    reported_date DATE NOT NULL,
    status        VARCHAR(20) NOT NULL,
    closed_date   DATE
);
CREATE INDEX IF NOT EXISTS ix_incident_date ON fact_incident(reported_date);
CREATE INDEX IF NOT EXISTS ix_incident_site ON fact_incident(site_id);

CREATE TABLE IF NOT EXISTS fact_eyfs_observation (
    id               SERIAL PRIMARY KEY,
    child_id         INTEGER NOT NULL REFERENCES dim_child(id),
    site_id          INTEGER NOT NULL REFERENCES dim_site(id),
    observation_date DATE NOT NULL,
    area             VARCHAR(30) NOT NULL,
    status           VARCHAR(20) NOT NULL,
    on_track         BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_eyfs_date ON fact_eyfs_observation(observation_date);
CREATE INDEX IF NOT EXISTS ix_eyfs_child ON fact_eyfs_observation(child_id);

CREATE TABLE IF NOT EXISTS fact_meal (
    id           SERIAL PRIMARY KEY,
    child_id     INTEGER NOT NULL REFERENCES dim_child(id),
    site_id      INTEGER NOT NULL REFERENCES dim_site(id),
    date         DATE NOT NULL,
    meal_type    VARCHAR(20) NOT NULL,
    intake_pct   INTEGER NOT NULL,
    allergy_flag BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_meal_date ON fact_meal(date);

CREATE TABLE IF NOT EXISTS fact_message (
    id               SERIAL PRIMARY KEY,
    site_id          INTEGER NOT NULL REFERENCES dim_site(id),
    parent_id        INTEGER REFERENCES dim_parent(id),
    staff_id         INTEGER REFERENCES dim_staff(id),
    sent_at          TIMESTAMP NOT NULL,
    direction        VARCHAR(12) NOT NULL,
    message_type     VARCHAR(20) NOT NULL,
    is_read          BOOLEAN NOT NULL DEFAULT FALSE,
    response_minutes INTEGER
);
CREATE INDEX IF NOT EXISTS ix_message_sent ON fact_message(sent_at);
CREATE INDEX IF NOT EXISTS ix_message_site ON fact_message(site_id);
