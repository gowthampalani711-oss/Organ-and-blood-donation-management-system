import os
import pymysql
from pymysql.cursors import DictCursor
from typing import Optional, List, Dict, Any, Union, Tuple
from werkzeug.security import generate_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", 3306))
DB_USER: str = os.getenv("DB_USER", "root")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
DB_NAME: str = os.getenv("DB_NAME", "organdonar")


def get_mysql_connection(create_db_if_missing: bool = True) -> pymysql.connections.Connection:
    """Establish and return an active connection to the MySQL database."""
    if create_db_if_missing:
        # Ensure target database exists
        server_conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            cursorclass=DictCursor,
            connect_timeout=5,
            charset="utf8mb4"
        )
        try:
            with server_conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            server_conn.commit()
        finally:
            server_conn.close()

    # Connect to the target database
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=DictCursor,
        connect_timeout=5,
        charset="utf8mb4",
        autocommit=True
    )
    return conn


def get_db_connection() -> pymysql.connections.Connection:
    """Get an active MySQL database connection."""
    return get_mysql_connection(create_db_if_missing=False)


class DBWrapper:
    """MySQL database context manager providing unified cursor and dictionary queries."""

    def __init__(self) -> None:
        self.conn: Optional[pymysql.connections.Connection] = None
        self.cursor: Optional[DictCursor] = None

    def __enter__(self) -> "DBWrapper":
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if self.conn:
                if exc_type is not None:
                    self.conn.rollback()
                else:
                    self.conn.commit()
        except Exception:
            pass
        finally:
            if self.cursor:
                try:
                    self.cursor.close()
                except Exception:
                    pass
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass

    def query(self, sql: str, params: Optional[Union[Tuple, List, Dict]] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return list of dictionary rows."""
        params = params or ()
        assert self.cursor is not None, "Database cursor is not open"
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def query_one(self, sql: str, params: Optional[Union[Tuple, List, Dict]] = None) -> Optional[Dict[str, Any]]:
        """Execute a SELECT query and return one dictionary row or None."""
        params = params or ()
        assert self.cursor is not None, "Database cursor is not open"
        self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def execute(self, sql: str, params: Optional[Union[Tuple, List, Dict]] = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return the last inserted row ID."""
        params = params or ()
        assert self.cursor is not None, "Database cursor is not open"
        self.cursor.execute(sql, params)
        if self.conn:
            try:
                self.conn.commit()
            except Exception:
                pass
        return self.cursor.lastrowid


def init_database() -> bool:
    """Initializes MySQL database tables and verifies default seed records."""
    mysql_conn: Optional[pymysql.connections.Connection] = None
    try:
        mysql_conn = get_mysql_connection(create_db_if_missing=True)
        print("[Database] Connected to MySQL successfully.")

        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                content = f.read()

            raw_queries = [q.strip() for q in content.split(";") if q.strip()]
            with mysql_conn.cursor() as cur:
                for query in raw_queries:
                    # Strip leading comments
                    clean_lines = [
                        line for line in query.splitlines()
                        if not line.strip().startswith("--") and not line.strip().startswith("/*")
                    ]
                    clean_query = " ".join(clean_lines).strip()
                    if not clean_query:
                        continue
                    if clean_query.upper().startswith("USE ") or clean_query.upper().startswith("CREATE DATABASE"):
                        continue
                    try:
                        cur.execute(clean_query)
                    except Exception:
                        pass

                # Auto-migrate schema changes if existing tables are present
                try:
                    # Check if 'phone' exists in 'admins'
                    cur.execute(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'admins' AND COLUMN_NAME = 'phone'",
                        (DB_NAME,)
                    )
                    if not cur.fetchone():
                        cur.execute("ALTER TABLE admins ADD COLUMN phone VARCHAR(15) NULL UNIQUE AFTER email")

                    # Check if 'attempts' exists in 'otp_verifications'
                    cur.execute(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'otp_verifications' AND COLUMN_NAME = 'attempts'",
                        (DB_NAME,)
                    )
                    if not cur.fetchone():
                        cur.execute("ALTER TABLE otp_verifications ADD COLUMN attempts INT DEFAULT 0 AFTER purpose")

                    # Check if 'max_attempts' exists in 'otp_verifications'
                    cur.execute(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'otp_verifications' AND COLUMN_NAME = 'max_attempts'",
                        (DB_NAME,)
                    )
                    if not cur.fetchone():
                        cur.execute("ALTER TABLE otp_verifications ADD COLUMN max_attempts INT DEFAULT 5 AFTER attempts")

                    # Ensure otp_code in otp_verifications is wide enough for SHA-256 hashes
                    cur.execute("ALTER TABLE otp_verifications MODIFY COLUMN otp_code VARCHAR(64) NOT NULL")

                    # Check if 'photo_url' exists in 'blood_donors'
                    cur.execute(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'blood_donors' AND COLUMN_NAME = 'photo_url'",
                        (DB_NAME,)
                    )
                    if not cur.fetchone():
                        cur.execute("ALTER TABLE blood_donors ADD COLUMN photo_url VARCHAR(255) DEFAULT '/static/img/default-avatar.png' AFTER availability_status")
                except Exception as migration_err:
                    print(f"[Database] Schema check/migration note: {migration_err}")

                # Ensure default SuperAdmin account exists with registered mobile number
                desired_email = "organdonation@gmail.com"
                desired_phone = os.getenv("ADMIN_REGISTERED_PHONE", "9876543210").strip() or "9876543210"
                desired_hash = generate_password_hash("AdminPassword@2026")

                cur.execute(
                    "SELECT id FROM admins WHERE LOWER(email) = %s OR LOWER(username) = 'admin' ORDER BY id LIMIT 1",
                    (desired_email.lower(),)
                )
                admin_row = cur.fetchone()

                if admin_row:
                    admin_id = admin_row["id"] if isinstance(admin_row, dict) else admin_row[0]
                    cur.execute(
                        "UPDATE admins SET username = %s, email = %s, phone = %s, password_hash = %s, full_name = %s, security_keyword = %s, role = %s WHERE id = %s",
                        ("admin", desired_email, desired_phone, desired_hash,
                         "Chief Medical Administrator", "LIFESAVER2026", "SuperAdmin", admin_id)
                    )
                else:
                    cur.execute(
                        "INSERT INTO admins (username, email, phone, password_hash, full_name, security_keyword, role) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        ("admin", desired_email, desired_phone, desired_hash,
                         "Chief Medical Administrator", "LIFESAVER2026", "SuperAdmin")
                    )

                # Seed default Tamil Nadu cities if empty
                cur.execute("SELECT COUNT(*) AS cnt FROM cities")
                city_cnt = cur.fetchone()
                count_val = city_cnt.get("cnt", 0) if isinstance(city_cnt, dict) else (city_cnt[0] if city_cnt else 0)

                if count_val == 0:
                    cities = [
                        ("Chennai", "சென்னை", "Tamil Nadu", 13.0827, 80.2707),
                        ("Coimbatore", "கோயம்புத்தூர்", "Tamil Nadu", 11.0168, 76.9558),
                        ("Madurai", "மதுரை", "Tamil Nadu", 9.9252, 78.1198),
                        ("Trichy", "திருச்சிராப்பள்ளி", "Tamil Nadu", 10.7905, 78.7047),
                        ("Salem", "சேலம்", "Tamil Nadu", 11.6643, 78.1460),
                        ("Erode", "ஈரோடு", "Tamil Nadu", 11.3410, 77.7172),
                        ("Tirunelveli", "திருநெல்வேலி", "Tamil Nadu", 8.7139, 77.7567),
                        ("Vellore", "வேலூர்", "Tamil Nadu", 12.9165, 79.1325),
                        ("Thanjavur", "தஞ்சாவூர்", "Tamil Nadu", 10.7870, 79.1378),
                        ("Dindigul", "திண்டுக்கல்", "Tamil Nadu", 10.3673, 77.9803),
                        ("Tiruppur", "திருப்பூர்", "Tamil Nadu", 11.1085, 77.3411),
                        ("Kanchipuram", "காஞ்சிபுரம்", "Tamil Nadu", 12.8342, 79.7036),
                        ("Nagercoil", "நாகர்கோவில்", "Tamil Nadu", 8.1833, 77.4119),
                        ("Cuddalore", "கடலூர்", "Tamil Nadu", 11.7480, 79.7714),
                        ("Karur", "கரூர்", "Tamil Nadu", 10.9601, 78.0766),
                        ("Hosur", "ஓசூர்", "Tamil Nadu", 12.7409, 77.8253),
                        ("Bengaluru", "பெங்களூரு", "Karnataka", 12.9716, 77.5946),
                        ("Kochi", "கொச்சி", "Kerala", 9.9312, 76.2673),
                        ("Hyderabad", "ஹைதராபாத்", "Telangana", 17.3850, 78.4867),
                    ]
                    cur.executemany(
                        "INSERT INTO cities (name_en, name_ta, state, latitude, longitude) VALUES (%s, %s, %s, %s, %s)",
                        cities
                    )

            mysql_conn.commit()
            print("[Database] MySQL schema verified and initialized.")
        return True
    except Exception as e:
        print(f"[Database] Error connecting or initializing MySQL: {e}")
        raise e
    finally:
        if mysql_conn:
            try:
                mysql_conn.close()
            except Exception:
                pass
