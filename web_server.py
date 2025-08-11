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
from datetime import datetime, date

# --- Database Setup ---
DB_FILE = "database.db"

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
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
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, report_data TEXT
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS archived_reports (
        id TEXT PRIMARY KEY, year INTEGER NOT NULL, month INTEGER NOT NULL, date TEXT NOT NULL,
        submitted_by TEXT, report_data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
    )''')
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
    if salt is None: salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt, key

def verify_password(salt, key, password_to_check):
    new_key = hash_password(password_to_check, salt)[1]
    return hmac.compare_digest(key, new_key)

# --- HTTP Request Handler ---
class APIHandler(BaseHTTPRequestHandler):
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

    def _handle_api_request(self):
        current_user_session = None
        try:
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
                if session_data:
                    current_user_session = dict(session_data)

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            action = request_data.get("action")
            payload = request_data.get("payload", {})

            if action != "login" and not current_user_session:
                self._set_api_headers(401)
                self.wfile.write(json.dumps({"status": "error", "message": "Unauthorized"}).encode('utf-8'))
                return

            response_data = self.handle_action(action, payload, current_user_session)
            self._set_api_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        except Exception as e:
            print(f"API Error: {e}")
            self._set_api_headers(500)
            self.wfile.write(json.dumps({"status": "error", "message": "Server error"}).encode('utf-8'))

    def handle_action(self, action, payload, session):
        is_admin = session.get("role") == "admin" if session else False
        admin_actions = ["list_users", "add_user", "update_user", "delete_user", "add_personnel", "update_personnel", "delete_personnel", "import_personnel", "get_status_reports", "archive_reports", "get_archived_reports", "get_dashboard_summary"]
        
        if action in admin_actions and not is_admin:
            return {"status": "error", "message": "คุณไม่มีสิทธิ์ดำเนินการ"}
        
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if action == "login":
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
            
            if action == "logout":
                token_to_delete = payload.get("token")
                if token_to_delete:
                    cursor.execute("DELETE FROM sessions WHERE token = ?", (token_to_delete,))
                    conn.commit()
                return {"status": "success", "message": "ออกจากระบบสำเร็จ"}

            if action == "get_dashboard_summary":
                today_str = date.today().isoformat()
                cursor.execute("SELECT DISTINCT department FROM personnel WHERE department IS NOT NULL AND department != ''")
                all_departments = [row['department'] for row in cursor.fetchall()]
                cursor.execute("SELECT DISTINCT department FROM status_reports WHERE date = ?", (today_str,))
                submitted_departments = [row['department'] for row in cursor.fetchall()]
                cursor.execute("SELECT report_data FROM status_reports WHERE date = ?", (today_str,))
                reports_today = cursor.fetchall()
                status_summary = {}
                total_reported_personnel = 0
                for report in reports_today:
                    items = json.loads(report['report_data'])
                    total_reported_personnel += len(items)
                    for item in items:
                        status = item.get('status', 'ไม่ระบุ')
                        status_summary[status] = status_summary.get(status, 0) + 1
                cursor.execute("SELECT COUNT(id) as total FROM personnel")
                total_personnel = cursor.fetchone()['total']
                total_on_duty = total_personnel - total_reported_personnel
                summary = {
                    "all_departments": all_departments, "submitted_departments": submitted_departments,
                    "status_summary": status_summary, "total_personnel": total_personnel,
                    "total_on_duty": total_on_duty
                }
                return {"status": "success", "summary": summary}

            if action == "list_users":
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

            if action == "list_personnel":
                search_term = payload.get("searchTerm", "").strip()
                base_query = "SELECT * FROM personnel"
                params = []
                where_clauses = []
                if not is_admin:
                    where_clauses.append("department = ?")
                    params.append(session.get("department"))
                if search_term:
                    search_clause = "(first_name LIKE ? OR last_name LIKE ? OR position LIKE ?)"
                    term = f"%{search_term}%"
                    where_clauses.append(search_clause)
                    params.extend([term, term, term])
                if where_clauses:
                    base_query += " WHERE " + " AND ".join(where_clauses)
                cursor.execute(base_query, params)
                personnel = [{k: escape(str(v)) if v is not None else '' for k, v in dict(row).items()} for row in cursor.fetchall()]
                return {"status": "success", "personnel": personnel}

            if action == "add_user":
                data = payload.get("data", {}); username = data.get("username")
                if not username or not data.get("password"): return {"status": "error", "message": "กรุณากรอก Username และ Password"}
                cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                if cursor.fetchone(): return {"status": "error", "message": "Username นี้มีผู้ใช้อยู่แล้ว"}
                salt, key = hash_password(data["password"])
                cursor.execute("INSERT INTO users (username, salt, key, rank, first_name, last_name, position, department, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (username, salt, key, data.get('rank', ''), data.get('first_name', ''), data.get('last_name', ''), data.get('position', ''), data.get('department', ''), data.get('role', 'user')))
                conn.commit()
                return {"status": "success", "message": f"เพิ่มผู้ใช้ '{escape(username)}' สำเร็จ"}

            if action == "update_user":
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

            if action == "delete_user":
                username = payload.get("username")
                if username == 'jeerawut': return {"status": "error", "message": "ไม่สามารถลบบัญชีผู้ดูแลระบบหลักได้"}
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                return {"status": "success", "message": f"ลบผู้ใช้ '{escape(username)}' สำเร็จ"}

            if action == "add_personnel":
                data = payload.get("data", {})
                required_fields = ['rank', 'first_name', 'last_name', 'position', 'specialty', 'department']
                if not all(field in data and data[field] for field in required_fields):
                    return {"status": "error", "message": "ข้อมูลไม่ครบถ้วน กรุณากรอกข้อมูลให้ครบทุกช่อง"}
                new_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO personnel (id, rank, first_name, last_name, position, specialty, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (new_id, data["rank"], data["first_name"], data["last_name"], data["position"], data["specialty"], data["department"]))
                conn.commit()
                return {"status": "success", "message": "เพิ่มข้อมูลกำลังพลสำเร็จ"}

            if action == "update_personnel":
                data = payload.get("data", {})
                required_fields = ['id', 'rank', 'first_name', 'last_name', 'position', 'specialty', 'department']
                if not all(field in data and data[field] for field in required_fields):
                    return {"status": "error", "message": "ข้อมูลไม่ครบถ้วน กรุณากรอกข้อมูลให้ครบทุกช่อง"}
                cursor.execute("UPDATE personnel SET rank=?, first_name=?, last_name=?, position=?, specialty=?, department=? WHERE id=?",
                               (data["rank"], data["first_name"], data["last_name"], data["position"], data["specialty"], data["department"], data["id"]))
                conn.commit()
                return {"status": "success", "message": "อัปเดตข้อมูลสำเร็จ"}

            if action == "delete_personnel":
                cursor.execute("DELETE FROM personnel WHERE id = ?", (payload.get("id"),))
                conn.commit()
                return {"status": "success", "message": "ลบข้อมูลสำเร็จ"}
            
            if action == "import_personnel":
                new_data = payload.get("personnel", [])
                cursor.execute("DELETE FROM personnel")
                for p_data in new_data:
                    cursor.execute("INSERT INTO personnel (id, rank, first_name, last_name, position, specialty, department) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (str(uuid.uuid4()), p_data['rank'], p_data['first_name'], p_data['last_name'], p_data['position'], p_data['specialty'], p_data['department']))
                conn.commit()
                return {"status": "success", "message": f"นำเข้าข้อมูลกำลังพลจำนวน {len(new_data)} รายการสำเร็จ"}

            if action == "submit_status_report":
                report_data = payload.get("report", {})
                report_id = str(uuid.uuid4())
                submitted_by = session.get("username")
                user_department = session.get("department")
                cursor.execute("INSERT INTO status_reports (id, date, submitted_by, department, report_data) VALUES (?, ?, ?, ?, ?)",
                               (report_id, report_data["date"], submitted_by, user_department, json.dumps(report_data["items"])))
                conn.commit()
                return {"status": "success", "message": "ส่งยอดกำลังพลสำเร็จ"}

            if action == "get_status_reports":
                cursor.execute("SELECT id, date, submitted_by, department, timestamp, report_data FROM status_reports ORDER BY timestamp DESC")
                reports = []
                for row in cursor.fetchall():
                    report = dict(row)
                    report["items"] = json.loads(report["report_data"])
                    del report["report_data"]
                    reports.append(report)
                return {"status": "success", "reports": reports}

            if action == "archive_reports":
                reports_to_archive = payload.get("reports", [])
                for report in reports_to_archive:
                    date_parts = report["date"].split('-')
                    year, month = int(date_parts[0]), int(date_parts[1])
                    cursor.execute("INSERT INTO archived_reports (id, year, month, date, submitted_by, report_data) VALUES (?, ?, ?, ?, ?, ?)",
                                   (str(uuid.uuid4()), year, month, report["date"], report["submitted_by"], json.dumps(report["items"])))
                report_ids_to_delete = [r['id'] for r in reports_to_archive]
                if report_ids_to_delete:
                    placeholders = ','.join('?' for _ in report_ids_to_delete)
                    cursor.execute(f"DELETE FROM status_reports WHERE id IN ({placeholders})", report_ids_to_delete)
                conn.commit()
                return {"status": "success", "message": f"เก็บรายงานจำนวน {len(reports_to_archive)} รายการสำเร็จ"}

            if action == "get_archived_reports":
                cursor.execute("SELECT id, year, month, date, submitted_by, report_data, timestamp FROM archived_reports ORDER BY year DESC, month DESC, date DESC")
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

            # --- เพิ่ม: Action สำหรับดูประวัติการส่ง ---
            if action == "get_submission_history":
                user_dept = session.get("department")
                if not user_dept:
                    return {"status": "error", "message": "ไม่พบข้อมูลแผนกของผู้ใช้"}

                history = []
                # Get from status_reports
                cursor.execute("SELECT id, date, submitted_by, department, timestamp, report_data FROM status_reports WHERE department = ? ORDER BY date DESC", (user_dept,))
                for row in cursor.fetchall():
                    report = dict(row)
                    report["items"] = json.loads(report["report_data"])
                    del report["report_data"]
                    history.append(report)
                
                # Get from archived_reports
                cursor.execute("SELECT username FROM users WHERE department = ?", (user_dept,))
                users_in_dept = [row['username'] for row in cursor.fetchall()]

                if users_in_dept:
                    placeholders = ','.join('?' for _ in users_in_dept)
                    cursor.execute(f"SELECT id, date, submitted_by, report_data, timestamp FROM archived_reports WHERE submitted_by IN ({placeholders}) ORDER BY date DESC", users_in_dept)
                    for row in cursor.fetchall():
                        report = dict(row)
                        report["items"] = json.loads(report["report_data"])
                        del report["report_data"]
                        report["department"] = user_dept
                        history.append(report)

                history.sort(key=lambda x: x['timestamp'], reverse=True)
                return {"status": "success", "history": history}


            return {"status": "error", "message": "ไม่รู้จักคำสั่งนี้"}
        
        finally:
            conn.close()

def run(server_class=HTTPServer, handler_class=APIHandler, port=9999):
    init_db()
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"เซิร์ฟเวอร์ระบบจัดการกำลังพลกำลังทำงานที่ http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
