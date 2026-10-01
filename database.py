# database.py - all SQLite code lives here
import hashlib
import hmac
import os
import sqlite3

DB_NAME = "localserve.db"
HASH_ROUNDS = 600_000  # how many times a password is scrambled

# Time slots every provider offers each day
SLOTS = ["10:00 AM", "11:00 AM", "12:00 PM", "02:00 PM",
         "03:00 PM", "04:00 PM", "05:00 PM"]


def get_connection():
    """Open a connection. Rows can be read like row["price"]."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Create all tables, then add sample data if empty."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            password TEXT,
            role TEXT
        )
    """)
    # Two accounts can never share one email
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            category TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            duration INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            customer_email TEXT,
            service_id INTEGER,
            service_name TEXT,
            provider_name TEXT,
            booking_date TEXT,
            booking_time TEXT,
            price INTEGER,
            status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER
        )
    """)

    # Older databases don't have user_id yet, so add it
    columns = [r["name"] for r in cur.execute("PRAGMA table_info(bookings)")]
    if "user_id" not in columns:
        cur.execute("ALTER TABLE bookings ADD COLUMN user_id INTEGER")

    # Add sample services only if the table is empty
    count = cur.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    if count == 0:
        samples = [
            ("Haircut", "Salon", "Style Studio",
             "Professional haircut and styling.", 300, 30),
            ("1 Bedroom Cleaning", "Home Cleaning", "CleanHome Services",
             "Complete cleaning of a 1 bedroom home.", 799, 90),
            ("Laptop Diagnosis", "Laptop Repair", "TechFix Solutions",
             "Complete laptop inspection and diagnosis.", 499, 60),
            ("Python Programming", "Tutoring", "Bright Tutors",
             "One-on-one Python programming lesson.", 500, 60),
            ("Event Photography", "Photography", "FrameWorks Studio",
             "Professional photography for your event.", 2500, 120),
            ("Personal Training Session", "Fitness Training", "FitZone Training",
             "One-on-one personal fitness training.", 700, 60),
        ]
        cur.executemany("""
            INSERT INTO services
            (service_name, category, provider_name, description, price, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        """, samples)

    conn.commit()
    conn.close()


# ---------- Users and passwords ----------
def hash_password(password):
    """Scramble a password with a random salt. Returns 'salt$hash' text."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt, HASH_ROUNDS)
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored):
    """Check a typed password against the stored 'salt$hash' text."""
    try:
        salt_hex, hash_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     bytes.fromhex(salt_hex), HASH_ROUNDS)
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_user(name, email, phone, password):
    """Create a customer account. Returns the new user id, or None if the
    email is already used."""
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO users (name, email, phone, password, role)
            VALUES (?, ?, ?, ?, 'customer')
        """, (name, email.lower(), phone, hash_password(password)))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def authenticate_user(email, password):
    """Return the user row if email and password are correct, else None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ? AND role = 'customer'",
                       (email.lower(),)).fetchone()
    conn.close()
    if row is None:
        hash_password(password)  # same waiting time whether or not the email exists
        return None
    return row if verify_password(password, row["password"]) else None


def get_customers():
    """Return customers for the admin. The password is NOT included."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, name, email, phone FROM users
        WHERE role = 'customer' ORDER BY id DESC
    """).fetchall()
    conn.close()
    return rows


# ---------- Services ----------
def get_services():
    """Return all services as a list of rows."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM services ORDER BY id").fetchall()
    conn.close()
    return rows


def get_service_by_id(service_id):
    """Return one service, or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM services WHERE id = ?",
                       (service_id,)).fetchone()
    conn.close()
    return row


def add_service(service_name, category, provider_name, description,
                price, duration):
    """Add a new service."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO services
        (service_name, category, provider_name, description, price, duration)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (service_name, category, provider_name, description, price, duration))
    conn.commit()
    conn.close()


def delete_service(service_id):
    """Delete a service. Old bookings keep their own copy of the service name."""
    conn = get_connection()
    conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
    conn.commit()
    conn.close()


# ---------- Bookings ----------
def get_booked_times(provider_name, booking_date):
    """Return the times already taken for this provider on this date.
    Rejected bookings free up their slot again."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT booking_time FROM bookings
        WHERE provider_name = ? AND booking_date = ? AND status != 'Rejected'
    """, (provider_name, booking_date)).fetchall()
    conn.close()
    return [r["booking_time"] for r in rows]


def is_slot_available(provider_name, booking_date, booking_time):
    """True if provider + date + time is not booked yet."""
    return booking_time not in get_booked_times(provider_name, booking_date)


def create_booking(name, phone, email, service, booking_date, booking_time,
                   user_id=None):
    """Save a booking. Returns the booking code, or None if the slot is taken."""
    # Safety check: the slot must still be free
    if not is_slot_available(service["provider_name"], booking_date, booking_time):
        return None

    conn = get_connection()
    # Booking code like LS-20260930-001 (counts bookings on that date)
    count = conn.execute("SELECT COUNT(*) FROM bookings WHERE booking_date = ?",
                         (booking_date,)).fetchone()[0]
    code = f"LS-{booking_date.replace('-', '')}-{count + 1:03d}"

    conn.execute("""
        INSERT INTO bookings
        (booking_code, customer_name, customer_phone, customer_email,
         service_id, service_name, provider_name, booking_date,
         booking_time, price, status, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
    """, (code, name, phone, email, service["id"], service["service_name"],
          service["provider_name"], booking_date, booking_time,
          service["price"], user_id))
    conn.commit()
    conn.close()
    return code


def get_user_bookings(user_id):
    """Return the bookings of ONE logged-in customer, newest first."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM bookings
        WHERE user_id = ?
        ORDER BY booking_date DESC, id DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows


def get_bookings():
    """Return ALL bookings (for the admin), newest first."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM bookings ORDER BY booking_date DESC, id DESC
    """).fetchall()
    conn.close()
    return rows


def update_booking_status(booking_id, new_status):
    """Change a booking's status (Pending / Confirmed / Rejected / Completed)."""
    conn = get_connection()
    conn.execute("UPDATE bookings SET status = ? WHERE id = ?",
                 (new_status, booking_id))
    conn.commit()
    conn.close()