# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import hashlib
import os
import hmac
import base64
import uuid
import sqlite3
import secrets 
from html import escape
from datetime import datetime, date, timedelta
from collections import defaultdict

# --- Database Setup ---
DB_FILE = "database.db"

# --- Helper Functions ---
def get_thai_public_holidays(year):
    """Returns a set of public holiday dates for a given year."""
    # หมายเหตุ: รายการวันหยุดนี้ควรได้รับการอัปเดตทุกปี
    # รายการสำหรับปี พ.ศ. 2025 (ค.ศ. 2025)
    holidays = {
        date(year, 1, 1),   # วันขึ้นปีใหม่
        date(year, 2, 26),  # วันมาฆบูชา
        date(year, 4, 7),   # วันหยุดชดเชยวันจักรี
        date(year, 4, 14),  # วันสงกรานต์
        date(year, 4, 15),  # วันสงกรานต์
        date(year, 4, 16),  # วันหยุดชดเชยวันสงกรานต์
        date(year, 5, 1),   # วันแรงงานแห่งชาติ
        date(year, 5, 5),   # วันหยุดชดเชยวันฉัตรมงคล
        date(year, 5, 26),  # วันวิสาขบูชา
        date(year, 6, 3),   # วันเฉลิมพระชนมพรรษาสมเด็จพระนางเจ้าฯ พระบรมราชินี
        date(year, 7, 25),  # วันอาสาฬหบูชา
        date(year, 7, 28),  # วันเฉลิมพระชนมพรรษาพระบาทสมเด็จพระวชิรเกล้าเจ้าอยู่หัว
        date(year, 8, 12),  # วันเฉลิมพระชนมพรรษาสมเด็จพระนางเจ้าสิริกิติ์ พระบรมราชินีนาถพันปีหลวง และวันแม่แห่งชาติ
        date(year, 10, 13), # วันคล้ายวันสวรรคต พระบาทสมเด็จพระบรมชนกาธิเบศร มหาภูมิพลอดุลยเดชมหาราช บรมนาถบพิตร
        date(year, 10, 23), # วันปิยมหาราช
        date(year, 12, 5),  # วันคล้ายวันพระบรมราชสมภพของรัชกาลที่ 9 วันชาติ และวันพ่อแห่งชาติ
        date(year, 12, 10), # วันรัฐธรรมนูญ
        date(year, 12, 31), # วันสิ้นปี
    }
    return holidays

def get_next_week_range_str():
    """Calculates and formats the specific dates for the next 5 working days, grouping consecutive days."""
    today = date.today()
    holidays_2025 = get_thai_public_holidays(2025)
    holidays_2026 = get_thai_public_holidays(2026)
    all_holidays = holidays_2025.union(holidays_2026)

    working_days = []
    current_day = today - timedelta(days=today.weekday()) + timedelta(weeks=1)

    while len(working_days) < 5:
        if current_day.weekday() < 5 and current_day not in all_holidays:
            working_days.append(current_day)
        current_day += timedelta(days=1)

    if not working_days:
        return ""

    thai_months_abbr = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    
    groups = []
    if working_days:
        current_group = [working_days[0]]
        for i in range(1, len(working_days)):
            if working_days[i] == working_days[i-1] + timedelta(days=1):
                current_group.append(working_days[i])
            else:
                groups.append(current_group)
                current_group = [working_days[i]]
        groups.append(current_group)

    parts = []
    for group in groups:
        start_date = group[0]
        end_date = group[-1]
        
        start_day = start_date.day
        start_month = thai_months_abbr[start_date.month - 1]
        start_year = str(start_date.year + 543)[-2:]
        
        end_day = end_date.day
        end_month = thai_months_abbr[end_date.month - 1]
        end_year = str(end_date.year + 543)[-2:]

        if len(group) == 1:
            parts.append(f"{start_day} {start_month}{start_year}")
        else:
            if start_year != end_year:
                parts.append(f"{start_day} {start_month}{start_year} - {end_day} {end_month}{end_year}")
            elif start_month != end_month:
                parts.append(f"{start_day} {start_month}- {end_day} {end_month}{end_year}")
            else:
                parts.append(f"{start_day}-{end_day} {start_month}{end_year}")
                
    return " และ ".join(parts)


# --- Database Functions ---
def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database, creating tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, salt BLOB NOT NULL, key BLOB NOT NULL, rank TEXT,
        first_name TEXT, last_name TEXT, position TEXT, department TEXT, role TEXT NOT NULL
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS personnel (
        id TEXT PRIMARY KEY, rank TEXT, first_name TEXT, last_name TEXT,
        position TEXT, specialty TEXT, department TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS status_reports (
        id TEXT PRIMARY KEY, date TEXT NOT NULL, submitted_by TEXT, department TEXT,
        timestamp DATETIME, report_data TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS archived_reports (
        id TEXT PRIMARY KEY, year INTEGER NOT NULL, month INTEGER NOT NULL, date TEXT NOT NULL,
        department TEXT, submitted_by TEXT, report_data TEXT, timestamp DATETIME
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
    )''')

    cursor.execute("PRAGMA table_info(archived_reports)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'department' not in columns:
        print("Updating archived_reports schema: adding 'department' column...")
        try:
            cursor.execute("ALTER TABLE archived_reports ADD COLUMN department TEXT")
        except sqlite3.OperationalError as e:
            print(f"Could not alter table: {e}")

    # Create a default admin user if it doesn't exist
    cursor.execute("SELECT * FROM users WHERE username = ?", ('jeerawut',))
    if not cursor.fetchone():
        print("กำลังสร้างผู้ดูแลระบบ 'jeerawut'...")
        salt, key = hash_password("253427")
        cursor.execute("""
        INSERT INTO users (username, salt, key, rank, first_name, last_name, position, department, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('jeerawut', salt, key, 'น.อ.', 'จีราวุฒิ', 'ผู้ดูแลระบบ', 'ผู้ดูแลระบบ', 'ส่วนกลาง', 'admin'))
    conn.commit()
    conn.close()
    print("ฐานข้อมูล SQLite พร้อมใช้งาน")

# --- Security Functions ---
def hash_password(password, salt=None):
    """Hashes a password with a salt using PBKDF2-HMAC-SHA256."""
    if salt is None: salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt, key

def verify_password(salt, key, password_to_check):
    """Verifies a password against a stored salt and key."""
    new_key = hash_password(password_to_check, salt)[1]
    return hmac.compare_digest(key, new_key)

# --- Action Handlers ---
def handle_login(payload, conn, cursor):
    username, password = payload.get("username"), payload.get("password")
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    if user_data and verify_password(user_data['salt'], user_data['key'], password):
        session_token = secrets.token_hex(16)
        user_info = dict(user_data)
        cursor.execute("INSERT INTO sessions (token, username) VALUES (?, ?)", (session_token, user_info["username"]))
        conn.commit()
        user_info.pop('salt', None); user_info.pop('key', None)
        return {"status": "success", "token": session_token, "user": user_info}
    return {"status": "error", "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}

def handle_logout(payload, conn, cursor):
    token_to_delete = payload.get("token")
    if token_to_delete:
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token_to_delete,))
        conn.commit()
    return {"status": "success", "message": "ออกจากระบบสำเร็จ"}

# --- START: การเปลี่ยนแปลง ---
def handle_get_dashboard_summary(payload, conn, cursor):
    cursor.execute("SELECT DISTINCT department FROM personnel WHERE department IS NOT NULL AND department != ''")
    all_departments = [row['department'] for row in cursor.fetchall()]
    
    # ดึงข้อมูลรายงานล่าสุดของแต่ละแผนก พร้อมข้อมูลผู้ส่ง
    query = """
    SELECT 
        sr.department, sr.report_data, sr.timestamp,
        u.rank, u.first_name, u.last_name
    FROM 
        status_reports sr
    JOIN 
        users u ON sr.submitted_by = u.username
    WHERE 
        sr.timestamp = (SELECT MAX(timestamp) FROM status_reports WHERE department = sr.department)
    """
    cursor.execute(query)
    
    submitted_info = {}
    for row in cursor.fetchall():
        items = json.loads(row['report_data'])
        submitter_fullname = f"{row['rank']} {row['first_name']} {row['last_name']}"
        submitted_info[row['department']] = {
            'submitter_fullname': submitter_fullname,
            'timestamp': row['timestamp'],
            'status_count': len(items)
        }

    # คำนวณยอดรวมสถานะทั้งหมด
    cursor.execute("SELECT report_data FROM status_reports")
    all_active_reports = cursor.fetchall()
    status_summary = {}
    
    for report in all_active_reports:
        items = json.loads(report['report_data'])
        for item in items:
            status = item.get('status', 'ไม่ระบุ')
            status_summary[status] = status_summary.get(status, 0) + 1
            
    cursor.execute("SELECT COUNT(id) as total FROM personnel")
    total_personnel = cursor.fetchone()['total']
    total_on_duty = total_personnel - sum(status_summary.values())

    summary = {
        "all_departments": all_departments, 
        "submitted_info": submitted_info,
        "status_summary": status_summary, 
        "total_personnel": total_personnel,
        "total_on_duty": total_on_duty,
        "weekly_date_range": get_next_week_range_str()
    }
    return {"status": "success", "summary": summary}
# --- END: การเปลี่ยนแปลง ---


def handle_list_users(payload, conn, cursor):
    search_term = payload.get("searchTerm", "").strip()
    query = "SELECT username, rank, first_name, last_name, position, department, role FROM users"
    params = []
    if search_term:
        query += " WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR department LIKE ?"
        term = f"%{search_term}%"
        params.extend([term, term, term, term])
    cursor.execute(query, params)
    users = [{k: escape(str(v)) if v is not None else '' for k, v in dict(row).items()} for row in cursor.fetchall()]
    return {"status": "success", "users": users}

def handle_list_personnel(payload, conn, cursor, session):
    search_term = payload.get("searchTerm", "").strip()
    base_query = "SELECT * FROM personnel"
    params = []
    where_clauses = []
    
    is_admin = session.get("role") == "admin"
    department = session.get("department")

    if not is_admin:
        where_clauses.append("department = ?")
        params.append(department)

    if search_term:
        search_clause = "(first_name LIKE ? OR last_name LIKE ? OR position LIKE ?)"
        term = f"%{search_term}%"
        where_clauses.append(search_clause)
        params.extend([term, term, term])

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
        
    cursor.execute(base_query, params)
    personnel = [{k: escape(str(v)) if v is not None else '' for k, v in dict(row).items()} for row in cursor.fetchall()]
    
    submission_status = None
    if not is_admin:
        cursor.execute("SELECT timestamp FROM status_reports WHERE department = ? ORDER BY timestamp DESC LIMIT 1", (department,))
        last_submission = cursor.fetchone()
        if last_submission:
            submission_status = {"timestamp": last_submission['timestamp']}

    return {"status": "success", "personnel": personnel, "submission_status": submission_status}


def handle_add_user(payload, conn, cursor):
    data = payload.get("data", {}); username = data.get("username")
    if not username or not data.get("password"): return {"status": "error", "message": "กรุณากรอก Username และ Password"}
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone(): return {"status": "error", "message": "Username นี้มีผู้ใช้อยู่แล้ว"}
    salt, key = hash_password(data["password"])
    cursor.execute("INSERT INTO users (username, salt, key, rank, first_name, last_name, position, department, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (username, salt, key, data.get('rank', ''), data.get('first_name', ''), data.get('last_name', ''), data.get('position', ''), data.get('department', ''), data.get('role', 'user')))
    conn.commit()
    return {"status": "success", "message": f"เพิ่มผู้ใช้ '{escape(username)}' สำเร็จ"}

def handle_update_user(payload, conn, cursor):
    data = payload.get("data", {}); username = data.get("username")
    if data.get("password"):
        salt, key = hash_password(data["password"])
        cursor.execute("UPDATE users SET rank=?, first_name=?, last_name=?, position=?, department=?, role=?, salt=?, key=? WHERE username=?",
                       (data.get('rank'), data.get('first_name'), data.get('last_name'), data.get('position', ''), data.get('department', ''), data.get('role', ''), salt, key, username))
    else:
        cursor.execute("UPDATE users SET rank=?, first_name=?, last_name=?, position=?, department=?, role=? WHERE username=?",
                       (data.get('rank'), data.get('first_name'), data.get('last_name', ''), data.get('position', ''), data.get('department', ''), data.get('role', ''), username))
    conn.commit()
    return {"status": "success", "message": f"อัปเดตข้อมูล '{escape(username)}' สำเร็จ"}

def handle_delete_user(payload, conn, cursor):
    username = payload.get("username")
    if username == 'jeerawut': return {"status": "error", "message": "ไม่สามารถลบบัญชีผู้ดูแลระบบหลักได้"}
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    return {"status": "success", "message": f"ลบผู้ใช้ '{escape(username)}' สำเร็จ"}

def handle_add_personnel(payload, conn, cursor):
    data = payload.get("data", {})
    required_fields = ['rank', 'first_name', 'last_name', 'position', 'specialty', 'department']
    if not all(field in data and data[field] for field in required_fields):
        return {"status": "error", "message": "ข้อมูลไม่ครบถ้วน กรุณากรอกข้อมูลให้ครบทุกช่อง"}
    new_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO personnel (id, rank, first_name, last_name, position, specialty, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (new_id, data["rank"], data["first_name"], data["last_name"], data["position"], data["specialty"], data["department"]))
    conn.commit()
    return {"status": "success", "message": "เพิ่มข้อมูลกำลังพลสำเร็จ"}

def handle_update_personnel(payload, conn, cursor):
    data = payload.get("data", {})
    required_fields = ['id', 'rank', 'first_name', 'last_name', 'position', 'specialty', 'department']
    if not all(field in data and data[field] for field in required_fields):
        return {"status": "error", "message": "ข้อมูลไม่ครบถ้วน กรุณากรอกข้อมูลให้ครบทุกช่อง"}
    cursor.execute("UPDATE personnel SET rank=?, first_name=?, last_name=?, position=?, specialty=?, department=? WHERE id=?",
                   (data["rank"], data["first_name"], data["last_name"], data["position"], data["specialty"], data["department"], data["id"]))
    conn.commit()
    return {"status": "success", "message": "อัปเดตข้อมูลสำเร็จ"}

def handle_delete_personnel(payload, conn, cursor):
    cursor.execute("DELETE FROM personnel WHERE id = ?", (payload.get("id"),))
    conn.commit()
    return {"status": "success", "message": "ลบข้อมูลสำเร็จ"}

def handle_import_personnel(payload, conn, cursor):
    new_data = payload.get("personnel", [])
    cursor.execute("DELETE FROM personnel")
    for p_data in new_data:
        cursor.execute("INSERT INTO personnel (id, rank, first_name, last_name, position, specialty, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (str(uuid.uuid4()), p_data['rank'], p_data['first_name'], p_data['last_name'], p_data['position'], p_data['specialty'], p_data['department']))
    conn.commit()
    return {"status": "success", "message": f"นำเข้าข้อมูลกำลังพลจำนวน {len(new_data)} รายการสำเร็จ"}

def handle_submit_status_report(payload, conn, cursor, session):
    report_data = payload.get("report", {})
    report_id = str(uuid.uuid4())
    submitted_by = session.get("username")
    user_department = report_data.get("department", session.get("department"))

    bkk_time = datetime.utcnow() + timedelta(hours=7)
    timestamp_str = bkk_time.strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("DELETE FROM status_reports WHERE department = ?", (user_department,))

    cursor.execute("INSERT INTO status_reports (id, date, submitted_by, department, report_data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                   (report_id, report_data["date"], submitted_by, user_department, json.dumps(report_data["items"]), timestamp_str))
    conn.commit()
    return {"status": "success", "message": "ส่งยอดกำลังพลสำเร็จ"}

def handle_get_status_reports(payload, conn, cursor):
    query = """
    SELECT 
        sr.id, sr.date, sr.department, sr.timestamp, sr.report_data,
        u.rank, u.first_name, u.last_name
    FROM 
        status_reports sr
    JOIN 
        users u ON sr.submitted_by = u.username
    ORDER BY 
        sr.timestamp DESC
    """
    cursor.execute(query)
    reports = []
    for row in cursor.fetchall():
        report = dict(row)
        report["items"] = json.loads(report["report_data"])
        del report["report_data"]
        reports.append(report)
    return {"status": "success", "reports": reports}

def handle_archive_reports(payload, conn, cursor):
    reports_to_archive = payload.get("reports", [])
    for report in reports_to_archive:
        date_parts = report["date"].split('-')
        year, month = int(date_parts[0]), int(date_parts[1])
        submitted_by_fullname = f"{report['rank']} {report['first_name']} {report['last_name']}"
        cursor.execute("INSERT INTO archived_reports (id, year, month, date, department, submitted_by, report_data, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (str(uuid.uuid4()), year, month, report["date"], report["department"], submitted_by_fullname, json.dumps(report["items"]), report["timestamp"]))
    
    cursor.execute("DELETE FROM status_reports")
    conn.commit()
    return {"status": "success", "message": f"เก็บรายงานและรีเซ็ตแดชบอร์ดสำเร็จ"}

def handle_get_archived_reports(payload, conn, cursor):
    cursor.execute("SELECT id, year, month, date, department, submitted_by, report_data, timestamp FROM archived_reports ORDER BY year DESC, month DESC, date DESC")
    archives = {}
    for row in cursor.fetchall():
        report = dict(row)
        report["items"] = json.loads(report["report_data"])
        del report["report_data"]
        year_key = str(report["year"])
        month_key = str(report["month"])
        if year_key not in archives: archives[year_key] = {}
        if month_key not in archives[year_key]: archives[year_key][month_key] = []
        archives[year_key][month_key].append(report)
    return {"status": "success", "archives": archives}

def handle_get_submission_history(payload, conn, cursor, session):
    user_dept = session.get("department")
    if not user_dept:
        return {"status": "error", "message": "ไม่พบข้อมูลแผนกของผู้ใช้"}
    
    query = """
    WITH all_reports AS (
        SELECT id, date, submitted_by, department, timestamp, report_data, 'active' as source 
        FROM status_reports 
        WHERE department = :dept
        UNION ALL
        SELECT id, date, submitted_by, department, timestamp, report_data, 'archived' as source
        FROM archived_reports 
        WHERE department = :dept
    )
    SELECT * FROM all_reports ORDER BY timestamp DESC
    """
    cursor.execute(query, {"dept": user_dept})
    
    history = []
    for row in cursor.fetchall():
        report = dict(row)
        report["items"] = json.loads(report["report_data"])
        del report["report_data"]
        history.append(report)

    return {"status": "success", "history": history}

def handle_get_report_for_editing(payload, conn, cursor):
    report_id = payload.get("id")
    if not report_id:
        return {"status": "error", "message": "ไม่พบ ID ของรายงาน"}

    cursor.execute("SELECT report_data, department FROM status_reports WHERE id = ?", (report_id,))
    report = cursor.fetchone()

    if not report:
        cursor.execute("SELECT report_data, department FROM archived_reports WHERE id = ?", (report_id,))
        report = cursor.fetchone()

    if report:
        report_data = json.loads(report['report_data'])
        return {"status": "success", "report": {"items": report_data, "department": report['department']}}
    else:
        return {"status": "error", "message": "ไม่พบข้อมูลรายงาน"}


# --- HTTP Request Handler ---
class APIHandler(BaseHTTPRequestHandler):
    
    ACTION_MAP = {
        "login": {"handler": handle_login, "auth_required": False},
        "logout": {"handler": handle_logout, "auth_required": True},
        "get_dashboard_summary": {"handler": handle_get_dashboard_summary, "auth_required": True, "admin_only": True},
        "list_users": {"handler": handle_list_users, "auth_required": True, "admin_only": True},
        "add_user": {"handler": handle_add_user, "auth_required": True, "admin_only": True},
        "update_user": {"handler": handle_update_user, "auth_required": True, "admin_only": True},
        "delete_user": {"handler": handle_delete_user, "auth_required": True, "admin_only": True},
        "list_personnel": {"handler": handle_list_personnel, "auth_required": True},
        "add_personnel": {"handler": handle_add_personnel, "auth_required": True, "admin_only": True},
        "update_personnel": {"handler": handle_update_personnel, "auth_required": True, "admin_only": True},
        "delete_personnel": {"handler": handle_delete_personnel, "auth_required": True, "admin_only": True},
        "import_personnel": {"handler": handle_import_personnel, "auth_required": True, "admin_only": True},
        "submit_status_report": {"handler": handle_submit_status_report, "auth_required": True},
        "get_status_reports": {"handler": handle_get_status_reports, "auth_required": True, "admin_only": True},
        "archive_reports": {"handler": handle_archive_reports, "auth_required": True, "admin_only": True},
        "get_archived_reports": {"handler": handle_get_archived_reports, "auth_required": True, "admin_only": True},
        "get_submission_history": {"handler": handle_get_submission_history, "auth_required": True},
        "get_report_for_editing": {"handler": handle_get_report_for_editing, "auth_required": True},
    }

    def _serve_static_file(self):
        path_map = {'/': '/login.html', '/main': '/main.html'}
        path = path_map.get(self.path, self.path)
        filepath = path.lstrip('/')
        if not os.path.exists(filepath):
            self.send_error(404, "File not found")
            return
        mimetypes = {'.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css'}
        mimetype = mimetypes.get(os.path.splitext(filepath)[1], 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.end_headers()
        with open(filepath, 'rb') as f: self.wfile.write(f.read())

    def do_GET(self):
        self._serve_static_file()

    def do_POST(self):
        if self.path == "/api":
            self._handle_api_request()
        else:
            self.send_error(404, "Endpoint not found")

    def _set_api_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def _get_session(self):
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header.split(' ')[1]
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.username, u.role, u.department 
                FROM sessions s 
                JOIN users u ON s.username = u.username 
                WHERE s.token = ?
            """, (session_token,))
            session_data = cursor.fetchone()
            conn.close()
            return dict(session_data) if session_data else None
        return None

    def _handle_api_request(self):
        action_name = "unknown"
        try:
            session = self._get_session()
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            action_name = request_data.get("action")
            payload = request_data.get("payload", {})

            action_config = self.ACTION_MAP.get(action_name)

            if not action_config:
                return self._send_json_response({"status": "error", "message": "ไม่รู้จักคำสั่งนี้"}, 404)

            if action_config.get("auth_required") and not session:
                return self._send_json_response({"status": "error", "message": "Unauthorized"}, 401)
            
            if action_config.get("admin_only") and (not session or session.get("role") != "admin"):
                 return self._send_json_response({"status": "error", "message": "คุณไม่มีสิทธิ์ดำเนินการ"}, 403)

            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                handler_kwargs = {"payload": payload, "conn": conn, "cursor": cursor}
                if action_name in ["list_personnel", "submit_status_report", "get_submission_history"]:
                    handler_kwargs["session"] = session

                response_data = action_config["handler"](**handler_kwargs)
                self._send_json_response(response_data)
            finally:
                conn.close()

        except json.JSONDecodeError:
            self._send_json_response({"status": "error", "message": "Invalid JSON format"}, 400)
        except Exception as e:
            print(f"API Error on action '{action_name}': {e}")
            self._send_json_response({"status": "error", "message": "Server error"}, 500)

    def _send_json_response(self, data, status_code=200):
        self._set_api_headers(status_code)
        self.wfile.write(json.dumps(data).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=APIHandler, port=9999):
    """Starts the web server."""
    init_db()
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"เซิร์ฟเวอร์ระบบจัดการกำลังพลกำลังทำงานที่ http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
