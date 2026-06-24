"""Realistic demo-data generator for the Nursery Analytics Platform.

Idempotent: if children already exist the seed is skipped (pass force=True to
re-seed after truncation). Uses numpy for fast, reproducible randomisation.
"""
from __future__ import annotations

import datetime as dt
from calendar import monthrange

import numpy as np
import psycopg

from app.core.config import settings
from app.core.security import hash_password

RNG = np.random.default_rng(42)
TODAY = dt.date.today()

FIRST_NAMES = ["Olivia", "Noah", "Amelia", "Oliver", "Isla", "George", "Ava", "Arthur",
               "Mia", "Leo", "Aria", "Muhammad", "Sofia", "Theo", "Lily", "Freddie",
               "Grace", "Hugo", "Ella", "Jack", "Ivy", "Charlie", "Maya", "Aarav"]
LAST_NAMES = ["Smith", "Patel", "Jones", "Khan", "Williams", "Brown", "Taylor", "Davies",
              "Wilson", "Evans", "Nguyen", "Okafor", "Ahmed", "Murphy", "Walsh", "Adeyemi",
              "Kowalski", "Rossi", "Garcia", "Chen"]
# name, borough, postcode, fill_factor, pay_health, incident_factor
# (varied so the multi-site ranking and benchmarking are realistic: Camden thrives,
#  Islington struggles with occupancy + arrears, etc.)
BOROUGHS = [("Camden Bright Beginnings", "Camden", "NW1 8NH", 0.95, 0.97, 0.8),
            ("Hackney Little Explorers", "Hackney", "E8 3RL", 0.90, 0.93, 1.0),
            ("Wandsworth Tiny Steps", "Wandsworth", "SW18 4GQ", 0.88, 0.95, 0.9),
            ("Islington Acorns Nursery", "Islington", "N1 2AB", 0.76, 0.85, 1.5),
            ("Greenwich Meadow Daycare", "Greenwich", "SE10 9LS", 0.84, 0.90, 1.1)]
ROOM_DEFS = [("Baby Room", "baby", 9, 3), ("Toddler Room", "toddler", 16, 4),
             ("Preschool Room", "preschool", 24, 8)]


def _dsn() -> str:
    return (
        f"host={settings.POSTGRES_HOST} port={settings.POSTGRES_PORT} "
        f"dbname={settings.POSTGRES_DB} user={settings.POSTGRES_USER} "
        f"password={settings.POSTGRES_PASSWORD}"
    )


def _weekdays(start: dt.date, end: dt.date) -> list[dt.date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    return days


def _month_starts(n: int) -> list[dt.date]:
    out, cur = [], TODAY.replace(day=1)
    for _ in range(n):
        out.append(cur)
        cur = (cur - dt.timedelta(days=1)).replace(day=1)
    return sorted(out)


def already_seeded(conn: psycopg.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM dim_child").fetchone()[0] > 0


# ─── dim_date ────────────────────────────────────────────────────────────────
def seed_dates(conn: psycopg.Connection) -> None:
    start = (TODAY - dt.timedelta(days=400)).replace(day=1)
    end = TODAY + dt.timedelta(days=120)
    rows, d = [], start
    months = ["", "January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    dows = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    while d <= end:
        rows.append((d, d.year, (d.month - 1) // 3 + 1, d.month, months[d.month],
                     d.day, d.weekday(), dows[d.weekday()], d.weekday() >= 5))
        d += dt.timedelta(days=1)
    conn.cursor().executemany(
        "INSERT INTO dim_date (date_key,year,quarter,month,month_name,day,dow,dow_name,is_weekend) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", rows)


# ─── main generator ──────────────────────────────────────────────────────────
def seed(force: bool = False) -> None:
    with psycopg.connect(_dsn()) as conn:
        if already_seeded(conn) and not force:
            print("[seed] data already present; skipping")
            _ensure_users(conn)
            conn.commit()
            return

        print("[seed] generating demo data ...")
        seed_dates(conn)
        cur = conn.cursor()

        # Sites
        site_ids = []
        profile_by_site: dict[int, tuple[float, float, float]] = {}
        for name, borough, postcode, fill, pay_health, inc_factor in BOROUGHS:
            cap = int(ROOM_DEFS[0][2] + ROOM_DEFS[1][2] + ROOM_DEFS[2][2])
            overhead = float(RNG.integers(28000, 42000))
            sid = cur.execute(
                "INSERT INTO dim_site (name,borough,postcode,capacity,opened_on,monthly_overhead) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (name, borough, postcode, cap, dt.date(2018, 9, 1), overhead),
            ).fetchone()[0]
            site_ids.append(sid)
            profile_by_site[sid] = (fill, pay_health, inc_factor)

        # Rooms
        room_by_site: dict[int, list[tuple[int, str, int, int]]] = {}
        for sid in site_ids:
            rooms = []
            for rname, rtype, rcap, ratio in ROOM_DEFS:
                rid = cur.execute(
                    "INSERT INTO dim_room (site_id,name,room_type,capacity,required_ratio) "
                    "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                    (sid, rname, rtype, rcap, ratio),
                ).fetchone()[0]
                rooms.append((rid, rtype, rcap, ratio))
            room_by_site[sid] = rooms

        # Staff
        staff_by_site: dict[int, list[int]] = {}
        titles = [("Nursery Manager", 6), ("Deputy Manager", 6), ("Room Leader", 3),
                  ("Practitioner", 3), ("Practitioner", 2), ("Apprentice", 2)]
        all_staff = []
        for sid in site_ids:
            staff_ids = []
            roster = titles + [("Practitioner", int(RNG.choice([2, 3]))) for _ in range(6)]
            for title, qual in roster:
                is_agency = bool(RNG.random() < 0.12)
                dbs_roll = RNG.random()
                dbs_status = "valid" if dbs_roll < 0.8 else ("expiring" if dbs_roll < 0.93 else "expired")
                dbs_expiry = TODAY + dt.timedelta(days=int(RNG.integers(-30, 720)))
                rate = round(float(RNG.uniform(11.5, 13.5)) + qual, 2)
                sfid = cur.execute(
                    "INSERT INTO dim_staff (site_id,first_name,last_name,role_title,qualification_level,"
                    "dbs_status,dbs_expiry,contract_hours,hourly_rate,is_agency,employment_status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active') RETURNING id",
                    (sid, RNG.choice(FIRST_NAMES), RNG.choice(LAST_NAMES), title, qual,
                     dbs_status, dbs_expiry, 37.5, rate, is_agency),
                ).fetchone()[0]
                staff_ids.append(sfid)
                all_staff.append((sfid, sid, title))
            staff_by_site[sid] = staff_ids

        # Parents + Children
        # tuple: (id, site_id, room_id, status, monthly_fee, funding, enrollment_date, room_type, part_time)
        child_records = []
        for sid in site_ids:
            rooms = room_by_site[sid]
            fill = profile_by_site[sid][0]
            for rid, rtype, rcap, ratio in rooms:
                # fill scaled by the site's occupancy profile (capped at capacity)
                n_active = min(rcap, int(round(rcap * fill * float(RNG.uniform(0.96, 1.04)))))
                n_wait = int(RNG.integers(2, 8))
                n_withdrawn = int(RNG.integers(0, 3))
                for status, count in (("active", n_active), ("waitlist", n_wait), ("withdrawn", n_withdrawn)):
                    for _ in range(count):
                        # age range per room
                        if rtype == "baby":
                            age_months = int(RNG.integers(4, 24))
                        elif rtype == "toddler":
                            age_months = int(RNG.integers(24, 36))
                        else:
                            age_months = int(RNG.integers(36, 58))
                        dob = TODAY - dt.timedelta(days=age_months * 30 + int(RNG.integers(0, 28)))
                        fn, ln = RNG.choice(FIRST_NAMES), RNG.choice(LAST_NAMES)
                        pid = cur.execute(
                            "INSERT INTO dim_parent (site_id,first_name,last_name,email,phone) "
                            "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                            (sid, RNG.choice(FIRST_NAMES), ln,
                             f"{fn.lower()}.{ln.lower()}{int(RNG.integers(1,999))}@example.com",
                             f"07{int(RNG.integers(100000000,999999999))}"),
                        ).fetchone()[0]
                        funding_roll = RNG.random()
                        funding_type = ("funded_30" if funding_roll < 0.25 else
                                        "funded_15" if funding_roll < 0.5 else "private")
                        base_fee = {"baby": 1750, "toddler": 1550, "preschool": 1400}[rtype]
                        monthly_fee = round(base_fee * float(RNG.uniform(0.95, 1.1)), 2)
                        enroll = TODAY - dt.timedelta(days=int(RNG.integers(20, 600)))
                        allergy = RNG.choice([None, None, None, "Nuts", "Dairy", "Egg", "Gluten"])
                        room_assign = rid if status == "active" else (rid if status == "withdrawn" else None)
                        cid = cur.execute(
                            "INSERT INTO dim_child (site_id,room_id,parent_id,first_name,last_name,dob,gender,"
                            "enrollment_date,status,funding_type,monthly_fee,allergies) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                            (sid, room_assign, pid, fn, ln, dob, RNG.choice(["male", "female"]),
                             enroll if status != "waitlist" else None, status, funding_type,
                             monthly_fee, allergy),
                        ).fetchone()[0]
                        part_time = bool(RNG.random() < 0.22)  # ~1 in 5 attend mornings only
                        child_records.append((cid, sid, rid, status, monthly_fee,
                                              funding_type, enroll, rtype, part_time))

        active_children = [c for c in child_records if c[3] == "active"]
        print(f"[seed] {len(child_records)} children ({len(active_children)} active), "
              f"{len(all_staff)} staff, {len(site_ids)} sites")

        _seed_enrollment_events(cur, child_records)
        _seed_attendance(cur, active_children)
        _seed_invoices_payments(cur, active_children, profile_by_site)
        _seed_shifts(cur, all_staff, room_by_site)
        _seed_incidents(cur, active_children, site_ids, profile_by_site)
        _seed_eyfs(cur, active_children)
        _seed_meals(cur, active_children)
        _seed_messages(cur, site_ids, staff_by_site)

        conn.commit()
        _ensure_users(conn, sample_child=active_children[0], sample_staff=all_staff[0])
        conn.commit()
        print("[seed] done")


# ─── fact generators ─────────────────────────────────────────────────────────
def _seed_enrollment_events(cur, child_records) -> None:
    rows = []
    for cid, sid, _rid, status, _fee, _fund, enroll, _rt, *_ in child_records:
        if status == "waitlist":
            rows.append((cid, sid, "enquiry", TODAY - dt.timedelta(days=int(RNG.integers(5, 60)))))
            rows.append((cid, sid, "waitlist_join", TODAY - dt.timedelta(days=int(RNG.integers(1, 30)))))
        else:
            rows.append((cid, sid, "enquiry", enroll - dt.timedelta(days=int(RNG.integers(20, 90)))))
            rows.append((cid, sid, "admission", enroll))
            if status == "withdrawn":
                rows.append((cid, sid, "withdrawal", enroll + dt.timedelta(days=int(RNG.integers(120, 400)))))
    cur.executemany(
        "INSERT INTO fact_enrollment_event (child_id,site_id,event_type,event_date) VALUES (%s,%s,%s,%s)", rows)


def _seasonal_factor(d: dt.date) -> float:
    """Lower attendance during typical UK holiday periods (Aug, late Dec, half-terms)."""
    if d.month == 8:
        return 0.78                      # summer holidays
    if d.month == 12 and d.day >= 18:
        return 0.6                       # Christmas break
    if d.month == 4 and d.day <= 14:
        return 0.85                      # Easter break
    if (d.month, d.day) in [(2, x) for x in range(12, 19)]:
        return 0.88                      # Feb half-term
    return 1.0


def _seed_attendance(cur, active_children) -> None:
    days = _weekdays(TODAY - dt.timedelta(days=120), TODAY)
    rows = []
    for cid, sid, rid, _st, _fee, _fund, _enr, _rt, part_time in active_children:
        base_rate = float(RNG.uniform(0.86, 0.97))
        for d in days:
            present = RNG.random() < base_rate * _seasonal_factor(d)
            if present:
                ci = dt.datetime.combine(d, dt.time(8, 0)) + dt.timedelta(minutes=int(RNG.integers(0, 90)))
                if part_time:
                    co = dt.datetime.combine(d, dt.time(12, 30)) + dt.timedelta(minutes=int(RNG.integers(-15, 30)))
                else:
                    co = dt.datetime.combine(d, dt.time(17, 0)) + dt.timedelta(minutes=int(RNG.integers(-30, 75)))
                late = co.time() > dt.time(18, 0)
                rows.append((cid, sid, rid, d, "present", ci, co, late))
            else:
                reason = RNG.choice(["absent_illness", "absent_holiday", "unexplained"], p=[0.55, 0.3, 0.15])
                rows.append((cid, sid, rid, d, str(reason), None, None, False))
    cur.executemany(
        "INSERT INTO fact_attendance (child_id,site_id,room_id,date,status,check_in,check_out,late_pickup) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", rows)


def _seed_invoices_payments(cur, active_children, profile_by_site) -> None:
    months = _month_starts(12)
    pay_rows = []
    for cid, sid, _rid, _st, fee, funding, enroll, _rt, *_ in active_children:
        pay_health = profile_by_site[sid][1]
        funding_amt = {"funded_30": fee * 0.45, "funded_15": fee * 0.22, "private": 0.0}.get(funding, 0.0)
        for m in months:
            if enroll and m < enroll.replace(day=1):
                continue
            issue = m
            due = m + dt.timedelta(days=7)
            discount = round(fee * 0.05, 2) if RNG.random() < 0.12 else 0.0
            net = round(fee - funding_amt - discount, 2)
            # status depends on recency and the site's payment health
            age_months = (TODAY.year - m.year) * 12 + (TODAY.month - m.month)
            if age_months >= 2:
                status = "paid" if RNG.random() < (0.985 * pay_health + 0.01) else "overdue"
            elif age_months == 1:
                status = "paid" if RNG.random() < (0.9 * pay_health) else RNG.choice(["unpaid", "overdue", "partial"])
            else:
                status = "paid" if RNG.random() < (0.7 * pay_health) else RNG.choice(["unpaid", "partial"])
            paid_date = None
            if status == "paid":
                paid_date = due + dt.timedelta(days=int(RNG.integers(-3, 10)))
            inv_id = cur.execute(
                "INSERT INTO fact_invoice (child_id,site_id,issue_date,due_date,period_month,amount,"
                "funding_amount,discount_amount,status,paid_date) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (cid, sid, issue, due, m, net, round(funding_amt, 2), discount, str(status), paid_date),
            ).fetchone()[0]
            if status in ("paid", "partial"):
                amt = net if status == "paid" else round(net * 0.5, 2)
                success = RNG.random() < 0.97
                pay_rows.append((inv_id, cid, sid, paid_date or due, amt,
                                 str(RNG.choice(["direct_debit", "card", "bank_transfer"], p=[0.7, 0.2, 0.1])),
                                 success, False))
    if pay_rows:
        cur.executemany(
            "INSERT INTO fact_payment (invoice_id,child_id,site_id,payment_date,amount,method,success,is_refund) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", pay_rows)


def _seed_shifts(cur, all_staff, room_by_site) -> None:
    days = _weekdays(TODAY - dt.timedelta(days=60), TODAY)
    rows = []
    for sfid, sid, _title in all_staff:
        rooms = room_by_site[sid]
        for d in days:
            if RNG.random() < 0.78:  # scheduled today
                absent = RNG.random() < 0.06
                room = int(RNG.choice([r[0] for r in rooms]))
                if absent:
                    rows.append((sfid, sid, room, d, 7.5, 0.0, 0.0, True,
                                 str(RNG.choice(["sick", "holiday", "unpaid"], p=[0.5, 0.4, 0.1]))))
                else:
                    ot = round(float(RNG.choice([0, 0, 0, 0.5, 1.0, 1.5])), 2)
                    rows.append((sfid, sid, room, d, 7.5, round(7.5 + ot, 2), ot, False, None))
    cur.executemany(
        "INSERT INTO fact_staff_shift (staff_id,site_id,room_id,date,hours_scheduled,hours_worked,"
        "overtime_hours,absent,absence_reason) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)


def _seed_incidents(cur, active_children, site_ids, profile_by_site) -> None:
    rows = []
    n = int(len(active_children) * 0.6)
    for _ in range(n):
        cid, sid, *_ = active_children[int(RNG.integers(0, len(active_children)))]
        inc_factor = profile_by_site[sid][2]
        if RNG.random() > min(0.6 * inc_factor, 0.95):   # sites with higher factor log more incidents
            continue
        itype = str(RNG.choice(["accident", "incident", "safeguarding", "medication"], p=[0.5, 0.25, 0.1, 0.15]))
        sev = str(RNG.choice(["low", "medium", "high"], p=[0.6, 0.3, 0.1]))
        reported = TODAY - dt.timedelta(days=int(RNG.integers(0, 180)))
        closed = RNG.random() < 0.78
        closed_date = reported + dt.timedelta(days=int(RNG.integers(1, 14))) if closed else None
        rows.append((cid, sid, itype, sev, reported, "closed" if closed else "open", closed_date))
    cur.executemany(
        "INSERT INTO fact_incident (child_id,site_id,incident_type,severity,reported_date,status,closed_date) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)", rows)


def _seed_eyfs(cur, active_children) -> None:
    areas = ["communication", "physical", "pse", "literacy", "numeracy"]
    rows = []
    for cid, sid, *_ in active_children:
        for _ in range(int(RNG.integers(3, 9))):  # observations over time
            area = str(RNG.choice(areas))
            roll = RNG.random()
            status = "emerging" if roll < 0.22 else ("expected" if roll < 0.8 else "exceeding")
            on_track = status != "emerging"
            od = TODAY - dt.timedelta(days=int(RNG.integers(0, 90)))
            rows.append((cid, sid, od, area, status, on_track))
    cur.executemany(
        "INSERT INTO fact_eyfs_observation (child_id,site_id,observation_date,area,status,on_track) "
        "VALUES (%s,%s,%s,%s,%s,%s)", rows)


def _seed_meals(cur, active_children) -> None:
    days = _weekdays(TODAY - dt.timedelta(days=14), TODAY)
    rows = []
    for cid, sid, *rest in active_children:
        allergy = RNG.random() < 0.18
        for d in days:
            if RNG.random() < 0.9:  # present that day
                for meal in ("breakfast", "lunch", "snack", "tea"):
                    intake = int(np.clip(RNG.normal(78, 18), 5, 100))
                    rows.append((cid, sid, d, meal, intake, allergy))
    cur.executemany(
        "INSERT INTO fact_meal (child_id,site_id,date,meal_type,intake_pct,allergy_flag) "
        "VALUES (%s,%s,%s,%s,%s,%s)", rows)


def _seed_messages(cur, site_ids, staff_by_site) -> None:
    rows = []
    for sid in site_ids:
        staff = staff_by_site[sid]
        for _ in range(int(RNG.integers(250, 450))):
            sent = dt.datetime.combine(TODAY - dt.timedelta(days=int(RNG.integers(0, 30))),
                                       dt.time(int(RNG.integers(7, 19)), int(RNG.integers(0, 59))))
            direction = str(RNG.choice(["inbound", "outbound"], p=[0.4, 0.6]))
            mtype = str(RNG.choice(["report", "message", "announcement"], p=[0.55, 0.35, 0.1]))
            is_read = RNG.random() < 0.84
            resp = int(RNG.integers(2, 240)) if direction == "inbound" and RNG.random() < 0.85 else None
            rows.append((sid, None, int(RNG.choice(staff)), sent, direction, mtype, is_read, resp))
    cur.executemany(
        "INSERT INTO fact_message (site_id,parent_id,staff_id,sent_at,direction,message_type,is_read,response_minutes) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", rows)


# ─── users ───────────────────────────────────────────────────────────────────
def _role_id(conn, slug: str) -> int:
    return conn.execute("SELECT id FROM roles WHERE slug=%s", (slug,)).fetchone()[0]


def _ensure_users(conn, sample_child=None, sample_staff=None) -> None:
    """Create the admin + one demo user per role (idempotent on email)."""
    site_row = conn.execute("SELECT id FROM dim_site ORDER BY id LIMIT 1").fetchone()
    site_id = site_row[0] if site_row else None
    child_id = sample_child[0] if sample_child else (
        (lambda r: r[0] if r else None)(conn.execute("SELECT id FROM dim_child WHERE status='active' LIMIT 1").fetchone()))
    staff_id = sample_staff[0] if sample_staff else (
        (lambda r: r[0] if r else None)(conn.execute("SELECT id FROM dim_staff LIMIT 1").fetchone()))

    users = [
        (settings.ADMIN_EMAIL, "Platform Administrator", settings.ADMIN_PASSWORD, "admin", None, None, None),
        ("management@lait.org.uk", "Maria Owner", "Manager123!", "management", site_id, None, None),
        ("accounts@lait.org.uk", "Alan Accounts", "Accounts123!", "accounts", site_id, None, None),
        ("teacher@lait.org.uk", "Tara Teacher", "Teacher123!", "teacher", site_id, None, staff_id),
        ("parent@lait.org.uk", "Priya Parent", "Parent123!", "parent", site_id, child_id, None),
    ]
    for email, name, pw, slug, sid, cid, sfid in users:
        exists = conn.execute("SELECT 1 FROM users WHERE email=%s", (email,)).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO users (email,full_name,hashed_password,role_id,site_id,linked_child_id,linked_staff_id,is_active) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE)",
            (email, name, hash_password(pw), _role_id(conn, slug), sid, cid, sfid),
        )
    print("[seed] demo users ensured (admin@lait.org.uk + 1 per role)")


def bootstrap_admin() -> None:
    """Production-safe: create ONLY the admin user from env (no demo data).

    Requires migrations to have run (roles exist). Idempotent on email.
    """
    with psycopg.connect(_dsn()) as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE email=%s", (settings.ADMIN_EMAIL,)).fetchone()
        if exists:
            print(f"[bootstrap] admin {settings.ADMIN_EMAIL} already exists; skipping")
            return
        role = conn.execute("SELECT id FROM roles WHERE slug='admin'").fetchone()
        if not role:
            raise RuntimeError("admin role missing — run migrations first")
        conn.execute(
            "INSERT INTO users (email,full_name,hashed_password,role_id,is_active) "
            "VALUES (%s,%s,%s,%s,TRUE)",
            (settings.ADMIN_EMAIL, "Platform Administrator",
             hash_password(settings.ADMIN_PASSWORD), role[0]),
        )
        conn.commit()
        print(f"[bootstrap] created admin {settings.ADMIN_EMAIL}")


if __name__ == "__main__":
    seed()
