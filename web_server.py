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
import time
import re
from email.utils import formatdate

# --- Database Setup ---
DB_FILE = "database.db"

# --- Configuration ---
FAILED_LOGIN_ATTEMPTS = {}
LOCKOUT_TIME = 300
MAX_ATTEMPTS = 5
SESSION_TIMEOUT_SECONDS = 1800 # 30 minutes
ITEMS_PER_PAGE = 15 # Pagination limit

# --- Helper Functions ---
def get_thai_public_holidays(year):
    holidays = {
        date(year, 1, 1), date(year, 2, 26), date(year, 4, 7), date(year, 4, 14), date(year, 4, 15),
        date(year, 4, 16), date(year, 5, 1), date(year, 5, 5), date(year, 5, 26), date(year, 6, 3),
        date(year, 7, 25), date(year, 7, 28), date(year, 8, 12), date(year, 10, 13), date(year, 10, 23),
        date(year, 12, 5), date(year, 12, 10), date(year, 12, 31),
    }
    return holidays

def get_next_week_range_str():
    today = date.today()
    all_holidays = get_thai_public_holidays(2025).union(get_thai_public_holidays(2026))
    working_days = []
    current_day = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
    while len(working_days) < 5:
        if current_day.weekday() < 5 and current_day not in all_holidays:
            working_days.append(current_day)
        current_day += timedelta(days=1)
    if not working_days: return ""
    thai_months_abbr = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    groups, parts = [], []
    if working_days:
        current_group = [working_days[0]]
        for i in range(1, len(working_days)):
            if working_days[i] == working_days[i-1] + timedelta(days=1):
                current_group.append(working_days[i])
            else:
                groups.append(current_group); current_group = [working_days[i]]
        groups.append(current_group)
    for group in groups:
        start_date, end_date = group[0], group[-1]
        start_day, start_month, start_year = start_date.day, thai_months_abbr[start_date.month - 1], str(start_date.year + 543)[-2:]
        end_day, end_month, end_year = end_date.day, thai_months_abbr[end_date.month - 1], str(end_date.year + 543)[-2:]
        if len(group) == 1: parts.append(f"{start_day} {start_month}{start_year}")
        else:
            if start_year != end_year: parts.append(f"{start_day} {start_month}{start_year} - {end_day} {end_month}{end_year}")
            elif start_month != end_month: parts.append(f"{start_day} {start_month}- {end_day} {end_month}{end_year}")
            else: parts.append(f"{start_day}-{end_day} {start_month}{end_year}")
    return " และ ".join(parts)

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; return conn

def init_db():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, salt BLOB NOT NULL, key BLOB NOT NULL, rank TEXT, first_name TEXT, last_name TEXT, position TEXT, department TEXT, role TEXT NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS personnel (id TEXT PRIMARY KEY, rank TEXT, first_name TEXT, last_name TEXT, position TEXT, specialty TEXT, department TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS status_reports (id TEXT PRIMARY KEY, date TEXT NOT NULL, submitted_by TEXT, department TEXT, timestamp DATETIME, report_data TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS archived_reports (id TEXT PRIMARY KEY, year INTEGER NOT NULL, month INTEGER NOT NULL, date TEXT NOT NULL, department TEXT, submitted_by TEXT, report_data TEXT, timestamp DATETIME)')
    cursor.execute('CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE)')
    cursor.execute("SELECT * FROM users WHERE username = ?", ('jeerawut',))
    if not cursor.fetchone():
        print("กำลังสร้างผู้ดูแลระบบ 'jeerawut'...")
        salt, key = hash_password("Jee@wut2534")
        cursor.execute("INSERT INTO users (username, salt, key, rank, first_name, last_name, position, department, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ('jeerawut', salt, key, 'น.อ.', 'จีราวุฒิ', 'ผู้ดูแลระบบ', 'ผู้ดูแลระบบ', 'ส่วนกลาง', 'admin'))
    conn.commit(); conn.close(); print("ฐานข้อมูล SQLite พร้อมใช้งาน")

# --- Security Functions ---
def hash_password(password, salt=None):
    if salt is None: salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt, key

def verify_password(salt, key, password_to_check):
    return hmac.compare_digest(key, hash_password(password_to_check, salt)[1])

def is_password_complex(password):
    if len(password) < 8: return False
    if not re.search("[a-z]", password): return False
    if not re.search("[A-Z]", password): return False
    if not re.search("[0-9]", password): return False
    return True

# --- Action Handlers ---
def handle_login(payload, conn, cursor, client_address):
    ip_address = client_address[0]
    if ip_address in FAILED_LOGIN_ATTEMPTS:
        attempts, last_attempt_time = FAILED_LOGIN_ATTEMPTS[ip_address]
        if attempts >= MAX_ATTEMPTS and time.time() - last_attempt_time < LOCKOUT_TIME:
            return {"status": "error", "message": "คุณพยายามล็อกอินผิดพลาดบ่อยเกินไป กรุณาลองใหม่อีกครั้งใน 5 นาที"}, None
    
    username, password = payload.get("username"), payload.get("password")
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    
    if user_data and verify_password(user_data['salt'], user_data['key'], password):
        if ip_address in FAILED_LOGIN_ATTEMPTS: del FAILED_LOGIN_ATTEMPTS[ip_address]
        session_token = secrets.token_hex(16)
        cursor.execute("INSERT INTO sessions (token, username, created_at) VALUES (?, ?, ?)", 
                       (session_token, user_data["username"], datetime.now()))
        conn.commit()
        user_info = {k: user_data[k] for k in user_data.keys() if k not in ['salt', 'key']}
        expires_time = time.time() + SESSION_TIMEOUT_SECONDS
        cookie_attrs = [f'session_token={session_token}', 'HttpOnly', 'Path=/', 'SameSite=Strict', 'Secure', f'Max-Age={SESSION_TIMEOUT_SECONDS}', f'Expires={formatdate(expires_time, usegmt=True)}']
        headers = [('Set-Cookie', '; '.join(cookie_attrs))]
        return {"status": "success", "user": user_info}, headers
    else:
        if ip_address in FAILED_LOGIN_ATTEMPTS: FAILED_LOGIN_ATTEMPTS[ip_address] = (FAILED_LOGIN_ATTEMPTS[ip_address][0] + 1, time.time())
        else: FAILED_LOGIN_ATTEMPTS[ip_address] = (1, time.time())
        return {"status": "error", "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}, None

def handle_logout(payload, conn, cursor, session):
    token_to_delete = session.get("token")
    if token_to_delete:
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token_to_delete,))
        conn.commit()
    headers = [('Set-Cookie', 'session_token=; HttpOnly; Path=/; SameSite=Strict; Secure; Expires=Thu, 01 Jan 1970 00:00:00 GMT')]
    return {"status": "success", "message": "ออกจากระบบสำเร็จ"}, headers

def handle_list_personnel(payload, conn, cursor, session):
    page = payload.get("page", 1)
    search_term = payload.get("searchTerm", "").strip()
    fetch_all = payload.get("fetchAll", False)
    offset = (page - 1) * ITEMS_PER_PAGE

    base_query = " FROM personnel"
    params = []
    where_clauses = []
    
    is_admin = session.get("role") == "admin"
    if not is_admin:
        where_clauses.append("department = ?")
        params.append(session.get("department"))

    if search_term:
        where_clauses.append("(first_name LIKE ? OR last_name LIKE ? OR position LIKE ?)")
        term = f"%{search_term}%"
        params.extend([term, term, term])

    where_clause_str = ""
    if where_clauses:
        where_clause_str = " WHERE " + " AND ".join(where_clauses)
    
    count_query = "SELECT COUNT(*) as total" + base_query + where_clause_str
    cursor.execute(count_query, params)
    total_items = cursor.fetchone()['total']

    data_query = "SELECT *" + base_query + where_clause_str
    if not fetch_all:
        data_query += " LIMIT ? OFFSET ?"
        params.extend([ITEMS_PER_PAGE, offset])

    cursor.execute(data_query, params)
    personnel = [{k: escape(str(v)) if v is not None else '' for k, v in dict(row).items()} for row in cursor.fetchall()]
    
    submission_status = None
    if not is_admin:
        cursor.execute("SELECT timestamp FROM status_reports WHERE department = ? ORDER BY timestamp DESC LIMIT 1", (session.get("department"),))
        last_submission = cursor.fetchone()
        if last_submission:
            submission_status = {"timestamp": last_submission['timestamp']}

    weekly_date_range = get_next_week_range_str()

    return {"status": "success", "personnel": personnel, "total": total_items, "page": page, "submission_status": submission_status, "weekly_date_range": weekly_date_range}

# ... (All other handler functions remain unchanged)
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
    
    weekly_date_range = get_next_week_range_str()
    
    return {"status": "success", "reports": reports, "weekly_date_range": weekly_date_range}

def handle_get_dashboard_summary(payload, conn, cursor):
    cursor.execute("SELECT DISTINCT department FROM personnel WHERE department IS NOT NULL AND department != ''")
    all_departments = [row['department'] for row in cursor.fetchall()]
    query = "SELECT sr.department, sr.report_data, sr.timestamp, u.rank, u.first_name, u.last_name FROM status_reports sr JOIN users u ON sr.submitted_by = u.username WHERE sr.timestamp = (SELECT MAX(timestamp) FROM status_reports WHERE department = sr.department)"
    cursor.execute(query)
    submitted_info = {}
    for row in cursor.fetchall():
        items = json.loads(row['report_data'])
        submitter_fullname = f"{row['rank']} {row['first_name']} {row['last_name']}"
        submitted_info[row['department']] = {'submitter_fullname': submitter_fullname, 'timestamp': row['timestamp'], 'status_count': len(items)}
    cursor.execute("SELECT report_data FROM status_reports")
    status_summary = defaultdict(int)
    for report in cursor.fetchall():
        for item in json.loads(report['report_data']):
            status_summary[item.get('status', 'ไม่ระบุ')] += 1
    cursor.execute("SELECT COUNT(id) as total FROM personnel")
    total_personnel = cursor.fetchone()['total']
    total_on_duty = total_personnel - sum(status_summary.values())
    summary = {"all_departments": all_departments, "submitted_info": submitted_info, "status_summary": dict(status_summary), "total_personnel": total_personnel, "total_on_duty": total_on_duty, "weekly_date_range": get_next_week_range_str()}
    return {"status": "success", "summary": summary}

def handle_list_users(payload, conn, cursor):
    page = payload.get("page", 1)
    search_term = payload.get("searchTerm", "").strip()
    offset = (page - 1) * ITEMS_PER_PAGE
    count_query = "SELECT COUNT(*) as total FROM users"
    data_query = "SELECT username, rank, first_name, last_name, position, department, role FROM users"
    params = []
    where_clause = ""
    if search_term:
        where_clause = " WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR department LIKE ?"
        term = f"%{search_term}%"
        params.extend([term, term, term, term])
    cursor.execute(count_query + where_clause, params)
    total_items = cursor.fetchone()['total']
    data_query += where_clause + " LIMIT ? OFFSET ?"
    params.extend([ITEMS_PER_PAGE, offset])
    cursor.execute(data_query, params)
    users = [{k: escape(str(v)) if v is not None else '' for k, v in dict(row).items()} for row in cursor.fetchall()]
    return {"status": "success", "users": users, "total": total_items, "page": page}

def handle_add_user(payload, conn, cursor):
    data = payload.get("data", {}); username = data.get("username"); password = data.get("password")
    if not username or not password: return {"status": "error", "message": "กรุณากรอก Username และ Password"}
    if not is_password_complex(password): return {"status": "error", "message": "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร และมีตัวพิมพ์เล็ก, พิมพ์ใหญ่, และตัวเลข"}
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone(): return {"status": "error", "message": "Username นี้มีผู้ใช้อยู่แล้ว"}
    salt, key = hash_password(password)
    cursor.execute("INSERT INTO users (username, salt, key, rank, first_name, last_name, position, department, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (username, salt, key, data.get('rank', ''), data.get('first_name', ''), data.get('last_name', ''), data.get('position', ''), data.get('department', ''), data.get('role', 'user')))
    conn.commit()
    return {"status": "success", "message": f"เพิ่มผู้ใช้ '{escape(username)}' สำเร็จ"}

def handle_update_user(payload, conn, cursor):
    data = payload.get("data", {}); username = data.get("username"); password = data.get("password")
    if password:
        if not is_password_complex(password): return {"status": "error", "message": "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร และมีตัวพิมพ์เล็ก, พิมพ์ใหญ่, และตัวเลข"}
        salt, key = hash_password(password)
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

def handle_get_personnel_details(payload, conn, cursor):
    person_id = payload.get("id")
    if not person_id: return {"status": "error", "message": "ไม่พบ ID ของกำลังพล"}
    cursor.execute("SELECT * FROM personnel WHERE id = ?", (person_id,))
    personnel_data = cursor.fetchone()
    if personnel_data: return {"status": "success", "personnel": dict(personnel_data)}
    return {"status": "error", "message": "ไม่พบข้อมูลกำลังพล"}

def handle_add_personnel(payload, conn, cursor):
    data = payload.get("data", {})
    if not all(data.get(f) for f in ['rank', 'first_name', 'last_name', 'position', 'specialty', 'department']):
        return {"status": "error", "message": "ข้อมูลไม่ครบถ้วน กรุณากรอกข้อมูลให้ครบทุกช่อง"}
    cursor.execute("INSERT INTO personnel (id, rank, first_name, last_name, position, specialty, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), data["rank"], data["first_name"], data["last_name"], data["position"], data["specialty"], data["department"]))
    conn.commit()
    return {"status": "success", "message": "เพิ่มข้อมูลกำลังพลสำเร็จ"}

def handle_update_personnel(payload, conn, cursor):
    data = payload.get("data", {})
    if not all(data.get(f) for f in ['id', 'rank', 'first_name', 'last_name', 'position', 'specialty', 'department']):
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
    for p in new_data:
        cursor.execute("INSERT INTO personnel (id, rank, first_name, last_name, position, specialty, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (str(uuid.uuid4()), p['rank'], p['first_name'], p['last_name'], p['position'], p['specialty'], p['department']))
    conn.commit()
    return {"status": "success", "message": f"นำเข้าข้อมูลกำลังพลจำนวน {len(new_data)} รายการสำเร็จ"}

def handle_submit_status_report(payload, conn, cursor, session):
    report_data = payload.get("report", {})
    submitted_by = session.get("username")
    user_department = report_data.get("department", session.get("department"))
    timestamp_str = (datetime.utcnow() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("DELETE FROM status_reports WHERE department = ?", (user_department,))
    cursor.execute("INSERT INTO status_reports (id, date, submitted_by, department, report_data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), report_data["date"], submitted_by, user_department, json.dumps(report_data["items"]), timestamp_str))
    conn.commit()
    return {"status": "success", "message": "ส่งยอดกำลังพลสำเร็จ"}

def handle_archive_reports(payload, conn, cursor):
    for report in payload.get("reports", []):
        report_date = report["date"]
        department = report["department"]
        cursor.execute("DELETE FROM archived_reports WHERE date = ? AND department = ?", (report_date, department))
        year, month = map(int, report_date.split('-')[:2])
        submitted_by = f"{report['rank']} {report['first_name']} {report['last_name']}"
        cursor.execute("INSERT INTO archived_reports (id, year, month, date, department, submitted_by, report_data, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (str(uuid.uuid4()), year, month, report_date, department, submitted_by, json.dumps(report["items"]), report["timestamp"]))
    cursor.execute("DELETE FROM status_reports")
    conn.commit()
    return {"status": "success", "message": "เก็บรายงานและรีเซ็ตแดชบอร์ดสำเร็จ"}

def handle_get_archived_reports(payload, conn, cursor):
    cursor.execute("SELECT * FROM archived_reports ORDER BY year DESC, month DESC, date DESC")
    archives = defaultdict(lambda: defaultdict(list))
    for row in cursor.fetchall():
        report = dict(row); report["items"] = json.loads(report["report_data"]); del report["report_data"]
        archives[str(report["year"])][str(report["month"])].append(report)
    return {"status": "success", "archives": dict(archives)}

def handle_get_submission_history(payload, conn, cursor, session):
    user_dept = session.get("department")
    if not user_dept: return {"status": "error", "message": "ไม่พบข้อมูลแผนกของผู้ใช้"}
    query = """
    SELECT id, date, submitted_by, department, timestamp, report_data, 'active' as source 
    FROM status_reports WHERE department = :dept 
    UNION ALL 
    SELECT id, date, submitted_by, department, timestamp, report_data, 'archived' as source 
    FROM archived_reports WHERE department = :dept 
    ORDER BY timestamp DESC
    """
    cursor.execute(query, {"dept": user_dept})
    history = []
    for row in cursor.fetchall():
        report = dict(row); report["items"] = json.loads(report["report_data"]); del report["report_data"]; history.append(report)
    return {"status": "success", "history": history}

def handle_get_report_for_editing(payload, conn, cursor):
    report_id = payload.get("id")
    if not report_id: return {"status": "error", "message": "ไม่พบ ID ของรายงาน"}
    cursor.execute("SELECT report_data, department FROM status_reports WHERE id = ?", (report_id,))
    report = cursor.fetchone()
    if not report: cursor.execute("SELECT report_data, department FROM archived_reports WHERE id = ?", (report_id,)); report = cursor.fetchone()
    if report: return {"status": "success", "report": {"items": json.loads(report['report_data']), "department": report['department']}}
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
        "get_personnel_details": {"handler": handle_get_personnel_details, "auth_required": True, "admin_only": True},
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
        if not os.path.exists(filepath): self.send_error(404, "File not found"); return
        mimetypes = {'.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css'}
        mimetype = mimetypes.get(os.path.splitext(filepath)[1], 'application/octet-stream')
        self.send_response(200); self.send_header('Content-type', mimetype); self.end_headers()
        with open(filepath, 'rb') as f: self.wfile.write(f.read())

    def do_GET(self): self._serve_static_file()
    def do_POST(self):
        if self.path == "/api": self._handle_api_request()
        else: self.send_error(404, "Endpoint not found")

    def _send_json_response(self, data, status_code=200, headers=None):
        self.send_response(status_code); self.send_header('Content-type', 'application/json')
        if headers:
            for key, value in headers: self.send_header(key, value)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _get_session(self):
        cookie_header = self.headers.get('Cookie')
        if not cookie_header: return None
        cookies = dict(item.strip().split('=', 1) for item in cookie_header.split(';') if '=' in item)
        session_token = cookies.get('session_token')
        if not session_token: return None
        
        conn = get_db_connection(); cursor = conn.cursor()
        
        expiry_limit = datetime.now() - timedelta(seconds=SESSION_TIMEOUT_SECONDS)
        cursor.execute("DELETE FROM sessions WHERE created_at < ?", (expiry_limit,))
        conn.commit()

        cursor.execute("SELECT u.username, u.role, u.department, s.created_at FROM sessions s JOIN users u ON s.username = u.username WHERE s.token = ?", (session_token,))
        session_data = cursor.fetchone()
        conn.close()
        
        if session_data:
            session_dict = dict(session_data); session_dict['token'] = session_token; return session_dict
        return None

    def _handle_api_request(self):
        action_name = "unknown"
        try:
            session = self._get_session()
            content_length = int(self.headers['Content-Length'])
            request_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            action_name, payload = request_data.get("action"), request_data.get("payload", {})
            action_config = self.ACTION_MAP.get(action_name)
            if not action_config: return self._send_json_response({"status": "error", "message": "ไม่รู้จักคำสั่งนี้"}, 404)
            if action_config.get("auth_required") and not session: return self._send_json_response({"status": "error", "message": "Unauthorized"}, 401)
            if action_config.get("admin_only") and (not session or session.get("role") != "admin"): return self._send_json_response({"status": "error", "message": "คุณไม่มีสิทธิ์ดำเนินการ"}, 403)
            
            conn = get_db_connection(); cursor = conn.cursor()
            try:
                handler_kwargs = {"payload": payload, "conn": conn, "cursor": cursor}
                if action_name == "login": handler_kwargs["client_address"] = self.client_address
                if session and action_name in ["logout", "list_personnel", "submit_status_report", "get_submission_history"]:
                    handler_kwargs["session"] = session

                response_data = action_config["handler"](**handler_kwargs)
                headers = None
                if isinstance(response_data, tuple): response_data, headers = response_data
                self._send_json_response(response_data, headers=headers)
            finally: conn.close()
        except Exception as e:
            print(f"API Error on action '{action_name}': {e}")
            self._send_json_response({"status": "error", "message": "Server error"}, 500)

def run(server_class=HTTPServer, handler_class=APIHandler, port=9999):
    init_db()
    httpd = server_class(('', port), handler_class)
    print(f"เซิร์ฟเวอร์ระบบจัดการกำลังพลกำลังทำงานที่ http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
