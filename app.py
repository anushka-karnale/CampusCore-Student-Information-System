# ============================================================
# CAMPUSCORE - STUDENT MANAGEMENT SYSTEM
# app.py
# ============================================================

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
    abort
)

import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import shutil
from datetime import datetime


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = "campuscore_secret_key"

DATABASE = "campuscore.db"

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads",
    "documents"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# ALLOWED DOCUMENT TYPES
# ============================================================

DOCUMENT_TYPES = [
    "Aadhaar Card",
    "Leaving Certificate",
    "Marksheet",
    "Birth Certificate",
    "Passport",
    "Domicile Certificate",
    "Caste Certificate",
    "Income Certificate",
    "Other"
]


# ============================================================
# ALLOWED FILE EXTENSIONS
# ============================================================

ALLOWED_EXTENSIONS = {
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "doc",
    "docx"
}


def allowed_file(filename):

    if not filename:
        return False

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE INITIALIZATION
# ============================================================


def init_db():

    conn = get_db_connection()

    cursor = conn.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT NOT NULL

        )
    """)


    # --------------------------------------------------------
    # DEFAULT ADMIN
    # --------------------------------------------------------

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role)

        VALUES (?, ?, ?)
    """, (
        "admin",
        "admin123",
        "admin"
    ))


    # --------------------------------------------------------
    # DEFAULT FACULTY
    # --------------------------------------------------------

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role)

        VALUES (?, ?, ?)
    """, (
        "faculty",
        "faculty123",
        "faculty"
    ))


    # --------------------------------------------------------
    # DEFAULT STUDENT
    # --------------------------------------------------------

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role)

        VALUES (?, ?, ?)
    """, (
        "student",
        "student123",
        "student"
    ))


    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            roll_no TEXT NOT NULL,

            name TEXT NOT NULL,

            email TEXT NOT NULL,

            phone TEXT,

            course TEXT NOT NULL,

            semester TEXT,

            address TEXT,

            user_id INTEGER,

            UNIQUE (roll_no, course),

            FOREIGN KEY (user_id)
                REFERENCES users(id)

        )
    """)


    # --------------------------------------------------------
    # ADD USER_ID TO OLD STUDENTS TABLE
    # --------------------------------------------------------

    student_columns = cursor.execute("""
        PRAGMA table_info(students)
    """).fetchall()

    student_column_names = [
        column[1]
        for column in student_columns
    ]

    if "user_id" not in student_column_names:

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN user_id INTEGER
        """)


    # --------------------------------------------------------
    # FACULTY
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT,

            phone TEXT,

            department TEXT,

            designation TEXT

        )
    """)


    # --------------------------------------------------------
    # COURSES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            course_name TEXT NOT NULL,

            course_code TEXT,

            department TEXT,

            duration TEXT

        )
    """)


    # --------------------------------------------------------
    # FACULTY COURSE ASSIGNMENT
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty_courses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            faculty_id INTEGER NOT NULL,

            course_id INTEGER NOT NULL,

            academic_year TEXT,

            semester TEXT,

            UNIQUE (
                faculty_id,
                course_id,
                academic_year,
                semester
            ),

            FOREIGN KEY (faculty_id)
                REFERENCES faculty(id)
                ON DELETE CASCADE,

            FOREIGN KEY (course_id)
                REFERENCES courses(id)
                ON DELETE CASCADE

        )
    """)


    # --------------------------------------------------------
    # ADD USER_ID TO FACULTY
    # --------------------------------------------------------

    faculty_columns = cursor.execute("""
        PRAGMA table_info(faculty)
    """).fetchall()

    faculty_column_names = [
        column[1]
        for column in faculty_columns
    ]


    if "user_id" not in faculty_column_names:

        cursor.execute("""
            ALTER TABLE faculty
            ADD COLUMN user_id INTEGER
        """)


    # --------------------------------------------------------
    # DOCUMENTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER,

            document_type TEXT NOT NULL,

            file_name TEXT NOT NULL,

            file_path TEXT NOT NULL,

            upload_date TEXT,

            FOREIGN KEY (student_id)
                REFERENCES students(id)

        )
    """)


    # --------------------------------------------------------
    # COLLEGE INFORMATION
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS college_info (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            college_name TEXT NOT NULL,

            university TEXT,

            academic_year TEXT,

            college_email TEXT,

            college_phone TEXT,

            website TEXT,

            address TEXT

        )
    """)


    # --------------------------------------------------------
    # ACADEMIC SETTINGS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS academic_settings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            academic_year TEXT NOT NULL,

            current_semester TEXT NOT NULL,

            next_semester TEXT,

            status TEXT NOT NULL

        )
    """)


    # --------------------------------------------------------
    # NOTIFICATION SETTINGS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            new_student INTEGER DEFAULT 1,

            new_faculty INTEGER DEFAULT 1,

            new_course INTEGER DEFAULT 1,

            document_uploaded INTEGER DEFAULT 1,

            missing_document INTEGER DEFAULT 1,

            system_notification INTEGER DEFAULT 1

        )
    """)

    
    # --------------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            message TEXT NOT NULL,

            notification_type TEXT DEFAULT 'General',

            target_role TEXT NOT NULL,

            created_at TEXT NOT NULL

        )
    """)




    # --------------------------------------------------------
    # SAVE CHANGES
    # --------------------------------------------------------

    conn.commit()

    conn.close()

# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required():

    if "user_id" not in session:

        return False

    return True


# ============================================================
# ADMIN REQUIRED
# ============================================================

def admin_required():

    if "user_id" not in session:

        return False

    if session.get("role") != "admin":

        return False

    return True


# ============================================================
# LOGIN
# ============================================================

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()

        password = request.form.get("password", "").strip()

        conn = get_db_connection()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
        """, (
            username,
            password
        )).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            session["role"] = user["role"]

            if user["role"] == "admin":

                return redirect(
                    url_for("admin_dashboard")
                )

            elif user["role"] == "faculty":

                return redirect(
                    url_for("faculty_dashboard")
                )

            else:

                return redirect(
                    url_for("student_dashboard")
                )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template("login.html")



@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        role = request.form.get("role", "").strip().lower()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not username or not role or not new_password or not confirm_password:
            flash("Please fill all fields.", "error")
            return redirect(url_for("forgot_password"))

        if new_password != confirm_password:
            flash("New password and confirm password do not match.", "error")
            return redirect(url_for("forgot_password"))

        allowed_roles = ["admin", "faculty", "student"]

        if role not in allowed_roles:
            flash("Invalid role selected.", "error")
            return redirect(url_for("forgot_password"))

        conn = get_db_connection()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND role = ?
            LIMIT 1
        """, (username, role)).fetchone()

        if user is None:
            conn.close()
            flash("Username and role do not match.", "error")
            return redirect(url_for("forgot_password"))

        conn.execute("""
            UPDATE users
            SET password = ?
            WHERE id = ?
        """, (new_password, user["id"]))

        conn.commit()
        conn.close()

        flash("Password reset successfully. Please login with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    total_faculty = conn.execute("""
        SELECT COUNT(*)
        FROM faculty
    """).fetchone()[0]

    total_courses = conn.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]

    total_documents = conn.execute("""
        SELECT COUNT(*)
        FROM documents
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_faculty=total_faculty,
        total_courses=total_courses,
        total_documents=total_documents
    )
# ============================================================
# ADMIN PROFILE
# ============================================================

@app.route("/admin/profile", methods=["GET", "POST"])
def admin_profile():

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    admin = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
        AND role = 'admin'
    """, (
        session["user_id"],
    )).fetchone()

    if not admin:
        conn.close()
        return redirect(url_for("logout"))

    if request.method == "POST":

        admin_name = request.form.get(
            "admin_name",
            ""
        ).strip()

        admin_email = request.form.get(
            "email",
            ""
        ).strip()

        admin_phone = request.form.get(
            "phone",
            ""
        ).strip()

        session["admin_name"] = admin_name
        session["admin_email"] = admin_email
        session["admin_phone"] = admin_phone

        conn.close()

        flash("Admin profile updated successfully.")

        return redirect(
            url_for("admin_profile")
        )

    admin_name = session.get(
        "admin_name",
        "CampusCore Administrator"
    )

    admin_email = session.get(
        "admin_email",
        ""
    )

    admin_phone = session.get(
        "admin_phone",
        ""
    )

    conn.close()

    return render_template(
        "admin_profile.html",
        admin=admin,
        admin_name=admin_name,
        admin_email=admin_email,
        admin_phone=admin_phone
    )
# ================= CHANGE PASSWORD =================
@app.route("/admin/change-password", methods=["GET", "POST"])
def change_password():

    # Admin login check
    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    # Get current admin
    conn = get_db_connection()

    admin = conn.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'admin'",
        (admin_id,)
    ).fetchone()

    conn.close()

    # If admin does not exist
    if not admin:
        return redirect(url_for("logout"))

    # Handle password change
    if request.method == "POST":

        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Check current password
        if current_password != admin["password"]:
            flash("Current password is incorrect.", "password_error")
            return redirect(url_for("change_password"))

        # Check empty new password
        if not new_password:
            flash("New password cannot be empty.", "password_error")
            return redirect(url_for("change_password"))

        # Check confirm password
        if new_password != confirm_password:
            flash("New password and confirm password do not match.", "password_error")
            return redirect(url_for("change_password"))

        # Check same password
        if current_password == new_password:
            flash(
                "New password must be different from current password.",
                "password_error"
            )
            return redirect(url_for("change_password"))

        # Update password
        conn = get_db_connection()

        conn.execute(
            """
            UPDATE users
            SET password = ?
            WHERE id = ? AND role = 'admin'
            """,
            (new_password, admin_id)
        )

        conn.commit()
        conn.close()

        # Success message
        flash("Password changed successfully.", "password_success")

        return redirect(url_for("settings"))

    # Open change password page
    return render_template("change_password.html")

@app.route("/admin/college-information", methods=["GET", "POST"])
def college_information():

    # Admin login check
    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Get existing college information
    college = conn.execute(
        "SELECT * FROM college_info ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # Save / Update college information
    if request.method == "POST":

        college_name = request.form.get("college_name", "").strip()
        university = request.form.get("university", "").strip()
        academic_year = request.form.get("academic_year", "").strip()
        college_email = request.form.get("college_email", "").strip()
        college_phone = request.form.get("college_phone", "").strip()
        website = request.form.get("website", "").strip()
        address = request.form.get("address", "").strip()

        # College name is required
        if not college_name:
            conn.close()

            flash(
                "College name is required.",
                "error"
            )

            return redirect(url_for("college_information"))

        # If information already exists → UPDATE
        if college:

            conn.execute(
                """
                UPDATE college_info
                SET
                    college_name = ?,
                    university = ?,
                    academic_year = ?,
                    college_email = ?,
                    college_phone = ?,
                    website = ?,
                    address = ?
                WHERE id = ?
                """,
                (
                    college_name,
                    university,
                    academic_year,
                    college_email,
                    college_phone,
                    website,
                    address,
                    college["id"]
                )
            )

            message = "College information updated successfully."

        # If no information exists → INSERT
        else:

            conn.execute(
                """
                INSERT INTO college_info
                (
                    college_name,
                    university,
                    academic_year,
                    college_email,
                    college_phone,
                    website,
                    address
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    college_name,
                    university,
                    academic_year,
                    college_email,
                    college_phone,
                    website,
                    address
                )
            )

            message = "College information saved successfully."

        conn.commit()
        conn.close()

        flash(message, "success")

        return redirect(url_for("college_information"))

    conn.close()

    return render_template(
        "college_information.html",
        college=college
    )

@app.route("/admin/academic-settings", methods=["GET", "POST"])
def academic_settings():

    # Admin login check
    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Get existing academic settings
    academic = conn.execute(
        "SELECT * FROM academic_settings ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # Save / Update academic settings
    if request.method == "POST":

        academic_year = request.form.get(
            "academic_year", ""
        ).strip()

        current_semester = request.form.get(
            "current_semester", ""
        ).strip()

        next_semester = request.form.get(
            "next_semester", ""
        ).strip()

        status = request.form.get(
            "status", ""
        ).strip()

        if not academic_year:
            conn.close()
            flash(
                "Academic year is required.",
                "error"
            )
            return redirect(
                url_for("academic_settings")
            )

        if not current_semester:
            conn.close()
            flash(
                "Current semester is required.",
                "error"
            )
            return redirect(
                url_for("academic_settings")
            )

        if academic:

            conn.execute(
                """
                UPDATE academic_settings

                SET
                    academic_year = ?,
                    current_semester = ?,
                    next_semester = ?,
                    status = ?

                WHERE id = ?
                """,
                (
                    academic_year,
                    current_semester,
                    next_semester,
                    status,
                    academic["id"]
                )
            )

            message = (
                "Academic settings updated successfully."
            )

        else:

            conn.execute(
                """
                INSERT INTO academic_settings
                (
                    academic_year,
                    current_semester,
                    next_semester,
                    status
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    academic_year,
                    current_semester,
                    next_semester,
                    status
                )
            )

            message = (
                "Academic settings saved successfully."
            )

        conn.commit()
        conn.close()

        flash(message, "success")

        return redirect(
            url_for("academic_settings")
        )

    conn.close()

    return render_template(
        "academic_settings.html",
        academic=academic
    )

@app.route("/admin/notification-settings", methods=["GET", "POST"])
def notification_settings():

    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    conn = get_db_connection()

    notifications = conn.execute(
        """
        SELECT *
        FROM notification_settings
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    if request.method == "POST":

        # Checkbox checked = 1
        # Checkbox unchecked = 0

        new_student = 1 if request.form.get("new_student") else 0

        new_faculty = 1 if request.form.get("new_faculty") else 0

        new_course = 1 if request.form.get("new_course") else 0

        document_uploaded = (
            1 if request.form.get("document_uploaded") else 0
        )

        missing_document = (
            1 if request.form.get("missing_document") else 0
        )

        system_notification = (
            1 if request.form.get("system_notification") else 0
        )

        if notifications:

            conn.execute(
                """
                UPDATE notification_settings

                SET
                    new_student = ?,
                    new_faculty = ?,
                    new_course = ?,
                    document_uploaded = ?,
                    missing_document = ?,
                    system_notification = ?

                WHERE id = ?
                """,
                (
                    new_student,
                    new_faculty,
                    new_course,
                    document_uploaded,
                    missing_document,
                    system_notification,
                    notifications["id"]
                )
            )

            message = (
                "Notification settings updated successfully."
            )

        else:

            conn.execute(
                """
                INSERT INTO notification_settings
                (
                    new_student,
                    new_faculty,
                    new_course,
                    document_uploaded,
                    missing_document,
                    system_notification
                )

                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_student,
                    new_faculty,
                    new_course,
                    document_uploaded,
                    missing_document,
                    system_notification
                )
            )

            message = (
                "Notification settings saved successfully."
            )

        conn.commit()
        conn.close()

        flash(message, "success")

        return redirect(
            url_for("notification_settings")
        )

    conn.close()

    return render_template(
        "notification_settings.html",
        notifications=notifications
    )


# ============================================================
# ADMIN - NOTIFICATIONS
# ============================================================

@app.route(
    "/admin/notifications",
    methods=["GET", "POST"]
)
def admin_notifications():

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    # --------------------------------------------------------
    # CREATE NOTIFICATION
    # --------------------------------------------------------

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        notification_type = request.form.get(
            "notification_type",
            "General"
        ).strip()

        target_role = request.form.get(
            "target_role",
            ""
        ).strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not title or not message or not target_role:

            conn.close()

            flash(
                "Please fill all required fields.",
                "error"
            )

            return redirect(
                url_for("admin_notifications")
            )

        # ----------------------------------------------------
        # VALID TARGET
        # ----------------------------------------------------

        allowed_targets = [
            "student",
            "faculty",
            "all"
        ]

        if target_role not in allowed_targets:

            conn.close()

            flash(
                "Invalid notification target.",
                "error"
            )

            return redirect(
                url_for("admin_notifications")
            )

        # ----------------------------------------------------
        # CURRENT DATE & TIME
        # ----------------------------------------------------

        created_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------------------
        # SAVE NOTIFICATION
        # ----------------------------------------------------

        conn.execute("""
            INSERT INTO notifications
            (
                title,
                message,
                notification_type,
                target_role,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            message,
            notification_type,
            target_role,
            created_at
        ))

        conn.commit()

        conn.close()

        flash(
            "Notification created successfully.",
            "success"
        )

        return redirect(
            url_for("admin_notifications")
        )

    # --------------------------------------------------------
    # GET ALL NOTIFICATIONS
    # --------------------------------------------------------

    notifications = conn.execute("""
        SELECT *
        FROM notifications
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_notifications.html",
        notifications=notifications
    )


# ============================================================
# ADMIN - DELETE NOTIFICATION
# ============================================================

@app.route(
    "/admin/notifications/delete/<int:notification_id>",
    methods=["POST"]
)
def delete_admin_notification(notification_id):

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    notification = conn.execute("""
        SELECT *
        FROM notifications
        WHERE id = ?
    """, (
        notification_id,
    )).fetchone()

    if notification is None:

        conn.close()

        flash(
            "Notification not found.",
            "error"
        )

        return redirect(
            url_for("admin_notifications")
        )

    conn.execute("""
        DELETE FROM notifications
        WHERE id = ?
    """, (
        notification_id,
    ))

    conn.commit()

    conn.close()

    flash(
        "Notification deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin_notifications")
    )



@app.route("/admin/database-backup")
def database_backup():

    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    # Current database path
    database_path = os.path.join(
        app.root_path,
        "campuscore.db"
    )

    # Backup folder
    backup_folder = os.path.join(
        app.root_path,
        "backups"
    )

    # Create backup folder if it does not exist
    os.makedirs(
        backup_folder,
        exist_ok=True
    )

    # Get existing backup files
    backup_files = []

    for file_name in os.listdir(backup_folder):

        if file_name.endswith(".db"):

            file_path = os.path.join(
                backup_folder,
                file_name
            )

            backup_files.append({
                "name": file_name,
                "size": round(
                    os.path.getsize(file_path) / 1024,
                    2
                ),
                "date": datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).strftime("%d-%m-%Y %I:%M %p")
            })

    # Latest backup first
    backup_files.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    return render_template(
        "database_backup.html",
        backup_files=backup_files
    )

@app.route(
    "/admin/database-backup/create",
    methods=["POST"]
)
def create_database_backup():

    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    database_path = os.path.join(
        app.root_path,
        "campuscore.db"
    )

    backup_folder = os.path.join(
        app.root_path,
        "backups"
    )

    os.makedirs(
        backup_folder,
        exist_ok=True
    )

    # Check database exists
    if not os.path.exists(database_path):

        flash(
            "Database file was not found.",
            "error"
        )

        return redirect(
            url_for("database_backup")
        )

    # Create unique backup filename
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_name = (
        f"campuscore_backup_{timestamp}.db"
    )

    backup_path = os.path.join(
        backup_folder,
        backup_name
    )

    # Copy database
    shutil.copy2(
        database_path,
        backup_path
    )

    flash(
        "Database backup created successfully.",
        "success"
    )

    return redirect(
        url_for("database_backup")
    )

@app.route(
    "/admin/database-backup/download/<filename>"
)
def download_database_backup(filename):

    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    backup_folder = os.path.join(
        app.root_path,
        "backups"
    )

    return send_from_directory(
        backup_folder,
        filename,
        as_attachment=True
    )

@app.route("/admin/about-campuscore")
def about_campuscore():

    admin_id = session.get("user_id")

    if not admin_id:
        return redirect(url_for("login"))

    return render_template(
        "about_campuscore.html"
    )
# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student/dashboard")
def student_dashboard():

    if not login_required():
        return redirect(
            url_for("login")
        )

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        # ---------------------------------------------
        # GET LOGGED-IN STUDENT
        # ---------------------------------------------

        student = conn.execute("""
            SELECT *
            FROM students
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()


        # ---------------------------------------------
        # STUDENT LOGIN NOT LINKED
        # ---------------------------------------------

        if student is None:

            flash(
                "Student profile is not linked with this login.",
                "error"
            )

            return redirect(
                url_for("login")
            )


        # ---------------------------------------------
        # GET STUDENT COURSES
        # ---------------------------------------------

        courses = conn.execute("""
            SELECT
                courses.course_name,
                courses.course_code,
                courses.department,
                courses.duration,
                faculty_courses.academic_year,
                faculty_courses.semester
            FROM faculty_courses
            INNER JOIN courses
                ON faculty_courses.course_id = courses.id
            WHERE courses.course_name = ?
            ORDER BY courses.course_name ASC
        """, (
            student["course"],
        )).fetchall()


        # ---------------------------------------------
        # DOCUMENT COUNT
        # ---------------------------------------------

        document_count = conn.execute("""
            SELECT COUNT(*)
            FROM documents
            WHERE student_id = ?
        """, (
            student["id"],
        )).fetchone()[0]


    finally:

        conn.close()


    return render_template(
        "student_dashboard.html",
        student=student,
        courses=courses,
        document_count=document_count
    )


# ============================================================
# FACULTY DASHBOARD
# ============================================================

# ============================================================
# FACULTY DASHBOARD
# ============================================================

@app.route("/faculty/dashboard")
def faculty_dashboard():

    if not login_required():
        return redirect(
            url_for("login")
        )

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        # ====================================================
        # LOGGED-IN FACULTY
        # ====================================================

        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()


        # ====================================================
        # DEFAULT VALUES
        # ====================================================

        students = []
        assigned_courses = []

        student_count = 0
        course_count = 0
        document_count = 0
        faculty_count = 0


        # ====================================================
        # FACULTY NOT LINKED
        # ====================================================

        if faculty is None:

            flash(
                "Faculty profile is not linked with this login.",
                "error"
            )

            conn.close()

            return redirect(
                url_for("login")
            )


        # ====================================================
        # FACULTY ID
        # ====================================================

        faculty_id = faculty["id"]


        # ====================================================
        # ASSIGNED COURSES
        # ====================================================

        assigned_courses = conn.execute("""
            SELECT
                courses.id,
                courses.course_name,
                courses.course_code,
                courses.department,
                courses.duration,
                faculty_courses.academic_year,
                faculty_courses.semester
            FROM faculty_courses

            INNER JOIN courses
                ON faculty_courses.course_id = courses.id

            WHERE faculty_courses.faculty_id = ?

            ORDER BY courses.course_name ASC
        """, (faculty_id,)).fetchall()


        # ====================================================
        # COURSE COUNT
        # ====================================================

        course_count = len(
            assigned_courses
        )


        # ====================================================
        # STUDENTS FROM ASSIGNED COURSES
        # ====================================================

        if assigned_courses:

            course_names = [
                course["course_name"]
                for course in assigned_courses
            ]

            placeholders = ",".join(
                ["?"] * len(course_names)
            )

            students = conn.execute(
                f"""
                SELECT
                    id,
                    roll_no,
                    name,
                    course,
                    semester,
                    email
                FROM students
                WHERE course IN ({placeholders})
                ORDER BY name ASC
                """,
                course_names
            ).fetchall()


            student_count = len(
                students
            )


        # ====================================================
        # DOCUMENT COUNT
        # ====================================================

        if students:

            student_ids = [
                student["id"]
                for student in students
            ]

            placeholders = ",".join(
                ["?"] * len(student_ids)
            )

            document_count = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM documents
                WHERE student_id IN ({placeholders})
                """,
                student_ids
            ).fetchone()[0]


        # ====================================================
        # TOTAL FACULTY COUNT
        # ====================================================

        faculty_count = conn.execute("""
            SELECT COUNT(*)
            FROM faculty
        """).fetchone()[0]


    finally:

        conn.close()


    # ========================================================
    # FACULTY DASHBOARD
    # ========================================================

    return render_template(
        "faculty_dashboard.html",

        student_count=student_count,

        course_count=course_count,

        document_count=document_count,

        faculty_count=faculty_count,

        faculty=faculty,

        students=students,

        courses=assigned_courses
    )

@app.route("/faculty/profile")
def faculty_profile():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:
        faculty = conn.execute("""
            SELECT
                faculty.id,
                faculty.name,
                faculty.email,
                faculty.phone,
                faculty.department,
                faculty.designation,
                faculty.user_id,
                users.username,
                users.role
            FROM faculty
            LEFT JOIN users
                ON faculty.user_id = users.id
            WHERE faculty.user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if faculty is None:
            flash(
                "Faculty profile is not linked with this login.",
                "error"
            )
            return redirect(url_for("login"))

        courses = conn.execute("""
            SELECT
                courses.course_name,
                courses.course_code,
                courses.department,
                courses.duration,
                faculty_courses.academic_year,
                faculty_courses.semester
            FROM faculty_courses
            INNER JOIN courses
                ON faculty_courses.course_id = courses.id
            WHERE faculty_courses.faculty_id = ?
            ORDER BY courses.course_name ASC
        """, (faculty["id"],)).fetchall()

    finally:
        conn.close()

    return render_template(
        "faculty_profile.html",
        faculty=faculty,
        courses=courses
    )

@app.route("/faculty/students")
def faculty_students():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if faculty is None:
            flash(
                "Faculty profile is not linked with this login.",
                "error"
            )
            return redirect(url_for("login"))

        faculty_id = faculty["id"]

        students = conn.execute("""
            SELECT DISTINCT
                students.id,
                students.roll_no,
                students.name,
                students.email,
                students.phone,
                students.course,
                students.semester
            FROM students

            INNER JOIN faculty_courses
                ON students.course = (
                    SELECT course_name
                    FROM courses
                    WHERE courses.id = faculty_courses.course_id
                )

            WHERE faculty_courses.faculty_id = ?

            ORDER BY students.name ASC
        """, (faculty_id,)).fetchall()

    finally:
        conn.close()

    return render_template(
        "faculty_students.html",
        faculty=faculty,
        students=students
    )

@app.route("/faculty/courses")
def faculty_courses():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if faculty is None:
            flash(
                "Faculty profile is not linked with this login.",
                "error"
            )
            return redirect(url_for("login"))

        faculty_id = faculty["id"]

        courses = conn.execute("""
            SELECT
                courses.id,
                courses.course_name,
                courses.course_code,
                courses.department,
                courses.duration,
                faculty_courses.academic_year,
                faculty_courses.semester
            FROM faculty_courses

            INNER JOIN courses
                ON faculty_courses.course_id = courses.id

            WHERE faculty_courses.faculty_id = ?

            ORDER BY courses.course_name ASC
        """, (faculty_id,)).fetchall()

    finally:
        conn.close()

    return render_template(
        "faculty_courses.html",
        faculty=faculty,
        courses=courses
    )

@app.route("/faculty/documents")
def faculty_documents():
    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:
        # Get logged-in faculty
        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if faculty is None:
            flash("Faculty profile is not linked with this login.", "error")
            return redirect(url_for("login"))

        faculty_id = faculty["id"]

        # Get documents of students belonging to faculty's assigned courses
        documents = conn.execute("""
            SELECT DISTINCT
                documents.id,
                documents.document_type,
                documents.file_name,
                documents.file_path,
                documents.upload_date,
                students.name AS student_name,
                students.roll_no,
                students.course
            FROM documents

            INNER JOIN students
                ON documents.student_id = students.id

            INNER JOIN faculty_courses
                ON students.course = (
                    SELECT course_name
                    FROM courses
                    WHERE courses.id = faculty_courses.course_id
                )

            WHERE faculty_courses.faculty_id = ?

            ORDER BY documents.upload_date DESC
        """, (faculty_id,)).fetchall()

    finally:
        conn.close()

    return render_template(
        "faculty_documents.html",
        faculty=faculty,
        documents=documents
    )

# ============================================================
# FACULTY DOCUMENT - VIEW
# ============================================================

@app.route("/faculty/document/view/<int:document_id>")
def faculty_view_document(document_id):

    # Check login
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:

        # Get document
        document = conn.execute("""
            SELECT
                documents.id,
                documents.student_id,
                documents.document_type,
                documents.file_name,
                documents.file_path,
                documents.upload_date,
                students.name AS student_name,
                students.roll_no,
                students.course
            FROM documents
            INNER JOIN students
                ON documents.student_id = students.id
            WHERE documents.id = ?
        """, (document_id,)).fetchone()

    finally:
        conn.close()

    # Document not found
    if document is None:
        abort(404)

    # File path missing
    if not document["file_path"]:
        abort(404)

    # Actual file path
    file_path = document["file_path"]

    full_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_path
    )

    # Physical file does not exist
    if not os.path.isfile(full_path):
        abort(404)

    # Open file in browser
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file_path,
        as_attachment=False
    )


# ============================================================
# FACULTY DOCUMENT - DOWNLOAD
# ============================================================

@app.route("/faculty/document/download/<int:document_id>")
def faculty_download_document(document_id):

    # Check login
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:

        # Get document
        document = conn.execute("""
            SELECT
                id,
                file_name,
                file_path
            FROM documents
            WHERE id = ?
        """, (document_id,)).fetchone()

    finally:
        conn.close()

    # Document not found
    if document is None:
        abort(404)

    # File path missing
    if not document["file_path"]:
        abort(404)

    # Actual file path
    file_path = document["file_path"]

    full_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_path
    )

    # Physical file does not exist
    if not os.path.isfile(full_path):
        abort(404)

    # Download file
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file_path,
        as_attachment=True,
        download_name=document["file_name"]
    )

# ============================================================
# FACULTY ACADEMIC REPORTS
# ============================================================

@app.route("/faculty/reports")
def faculty_reports():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        # ----------------------------------------------------
        # LOGGED-IN FACULTY
        # ----------------------------------------------------

        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if faculty is None:
            flash(
                "Faculty profile is not linked with this login.",
                "error"
            )
            return redirect(url_for("login"))

        faculty_id = faculty["id"]

        # ----------------------------------------------------
        # ASSIGNED COURSES
        # ----------------------------------------------------

        courses = conn.execute("""
            SELECT
                courses.id,
                courses.course_name,
                courses.course_code,
                courses.department,
                courses.duration,
                faculty_courses.academic_year,
                faculty_courses.semester
            FROM faculty_courses

            INNER JOIN courses
                ON faculty_courses.course_id = courses.id

            WHERE faculty_courses.faculty_id = ?

            ORDER BY courses.course_name ASC
        """, (faculty_id,)).fetchall()

        # ----------------------------------------------------
        # STUDENTS FROM ASSIGNED COURSES
        # ----------------------------------------------------

        if courses:

            course_names = [
                course["course_name"]
                for course in courses
            ]

            placeholders = ",".join(
                ["?"] * len(course_names)
            )

            students = conn.execute(
                f"""
                SELECT
                    id,
                    roll_no,
                    name,
                    email,
                    phone,
                    course,
                    semester
                FROM students
                WHERE course IN ({placeholders})
                ORDER BY name ASC
                """,
                course_names
            ).fetchall()

        else:

            students = []

        # ----------------------------------------------------
        # DOCUMENTS
        # ----------------------------------------------------

        if students:

            student_ids = [
                student["id"]
                for student in students
            ]

            placeholders = ",".join(
                ["?"] * len(student_ids)
            )

            documents = conn.execute(
                f"""
                SELECT
                    documents.id,
                    documents.student_id,
                    documents.document_type,
                    documents.file_name,
                    documents.upload_date,
                    students.name AS student_name,
                    students.roll_no,
                    students.course
                FROM documents

                INNER JOIN students
                    ON documents.student_id = students.id

                WHERE documents.student_id IN ({placeholders})

                ORDER BY documents.id DESC
                """,
                student_ids
            ).fetchall()

        else:

            documents = []

    finally:

        conn.close()


# ============================================================
# FACULTY ACADEMIC REPORTS
# ============================================================

@app.route("/faculty/academic-reports")
def faculty_academic_reports():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        # ----------------------------------------------------
        # GET LOGGED-IN FACULTY
        # ----------------------------------------------------

        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if faculty is None:

            flash(
                "Faculty profile is not linked with this login.",
                "error"
            )

            return redirect(url_for("login"))


        faculty_id = faculty["id"]


        # ----------------------------------------------------
        # GET FACULTY ASSIGNED COURSES
        # ----------------------------------------------------

        courses = conn.execute("""
            SELECT
                courses.id,
                courses.course_name,
                courses.course_code,
                courses.department,
                courses.duration,
                faculty_courses.academic_year,
                faculty_courses.semester
            FROM faculty_courses

            INNER JOIN courses
                ON faculty_courses.course_id = courses.id

            WHERE faculty_courses.faculty_id = ?

            ORDER BY courses.course_name ASC
        """, (faculty_id,)).fetchall()


        # ----------------------------------------------------
        # GET STUDENTS OF FACULTY COURSES
        # ----------------------------------------------------

        students = []

        student_count = 0


        if courses:

            course_names = [
                course["course_name"]
                for course in courses
            ]


            placeholders = ",".join(
                ["?"] * len(course_names)
            )


            students = conn.execute(
                f"""
                SELECT
                    id,
                    roll_no,
                    name,
                    email,
                    phone,
                    course,
                    semester

                FROM students

                WHERE course IN ({placeholders})

                ORDER BY name ASC
                """,

                course_names

            ).fetchall()


            student_count = len(students)


    finally:

        conn.close()


    # --------------------------------------------------------
    # SEND DATA TO ACADEMIC REPORT PAGE
    # --------------------------------------------------------

    return render_template(

        "faculty_academic_reports.html",

        faculty=faculty,

        courses=courses,

        students=students,

        student_count=student_count

    )
@app.route("/admin/students/add", methods=["GET", "POST"])
def add_student():

    if not admin_required():
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form.get("name")
        roll_no = request.form.get("roll_no")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        course = request.form.get("course")
        semester = request.form.get("semester")

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO students
            (name, roll_no, email, phone, address, course,semester)
            VALUES (?, ?, ?, ?, ?, ?,?)
        """, (
            name,
            roll_no,
            email,
            phone,
            address,
            course,
            semester
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_students"))

    return render_template("add_student.html")


@app.route("/admin/students/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()

    if student is None:
        conn.close()
        return redirect(url_for("view_students"))

    if request.method == "POST":

        name = request.form.get("name")
        roll_no = request.form.get("roll_no")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        course = request.form.get("course")
        semester = request.form.get("semester")

        conn.execute("""
            UPDATE students
            SET name = ?,
                roll_no = ?,
                email = ?,
                phone = ?,
                address = ?,
                course = ?,
                semester = ?
            WHERE id = ?
        """, (
            name,
            roll_no,
            email,
            phone,
            address,
            course,
            semester,
            student_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_students"))

    conn.close()

    return render_template(
        "edit_student.html",
        student=student
    )
@app.route("/admin/students/delete/<int:student_id>")
def delete_student(student_id):

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (student_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("view_students"))

@app.route("/admin/students")
def view_students():

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "view_students.html",
        students=students
    )


@app.route("/student/profile")
def student_profile():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        student = conn.execute("""
            SELECT *
            FROM students
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

    finally:
        conn.close()

    if student is None:

        flash(
            "Student profile is not linked with this login.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "student_profile.html",
        student=student
    )

@app.route("/student/courses")
def student_courses():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        # GET LOGGED-IN STUDENT
        student = conn.execute("""
            SELECT *
            FROM students
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if student is None:

            flash(
                "Student profile is not linked with this login.",
                "error"
            )

            return redirect(url_for("login"))

        # GET STUDENT'S COURSE INFORMATION
        courses = conn.execute("""
            SELECT
                courses.id,
                courses.course_name,
                courses.course_code,
                courses.department,
                courses.duration,
                faculty_courses.academic_year,
                faculty_courses.semester
            FROM faculty_courses
            INNER JOIN courses
                ON faculty_courses.course_id = courses.id
            WHERE courses.course_name = ?
            ORDER BY courses.course_name ASC
        """, (
            student["course"],
        )).fetchall()

    finally:
        conn.close()

    return render_template(
        "student_courses.html",
        student=student,
        courses=courses
    )


@app.route(
    "/student/documents",
    methods=["GET", "POST"]
)
def student_documents():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not login_required():

        return redirect(
            url_for("login")
        )

    # GET LOGGED-IN USER
    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        # ----------------------------------------------------
        # GET LOGGED-IN STUDENT
        # ----------------------------------------------------

        student = conn.execute("""
            SELECT *
            FROM students
            WHERE user_id = ?
            LIMIT 1
        """, (
            user_id,
        )).fetchone()

        if student is None:

            flash(
                "Student profile is not linked with this login.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        # ====================================================
        # UPLOAD DOCUMENT
        # ====================================================

        if request.method == "POST":

            # ------------------------------------------------
            # GET FORM DATA
            # ------------------------------------------------

            document_type = request.form.get(
                "document_type",
                ""
            ).strip()

            document_file = request.files.get(
                "document_file"
            )

            # ------------------------------------------------
            # CHECK DOCUMENT TYPE
            # ------------------------------------------------

            if not document_type:

                flash(
                    "Please select document type.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            # ------------------------------------------------
            # CHECK FILE
            # ------------------------------------------------

            if (
                document_file is None
                or not document_file.filename
            ):

                flash(
                    "Please choose a document file.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            # ------------------------------------------------
            # ALLOWED FILE TYPES
            # ------------------------------------------------

            allowed_extensions = {
                "pdf",
                "jpg",
                "jpeg",
                "png",
                "doc",
                "docx"
            }

            original_filename = (
                document_file.filename
            )

            if "." not in original_filename:

                flash(
                    "Invalid file type.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            extension = (
                original_filename
                .rsplit(".", 1)[1]
                .lower()
            )

            if extension not in allowed_extensions:

                flash(
                    "Invalid file type. "
                    "Allowed: PDF, JPG, JPEG, PNG, DOC, DOCX.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            # ------------------------------------------------
            # FILE SIZE CHECK
            # Maximum 10 MB
            # ------------------------------------------------

            document_file.seek(
                0,
                2
            )

            file_size = document_file.tell()

            document_file.seek(0)

            max_size = (
                10 * 1024 * 1024
            )

            if file_size > max_size:

                flash(
                    "File size must be 10 MB or less.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            # ------------------------------------------------
            # CREATE SAFE UNIQUE FILE NAME
            # ------------------------------------------------

            from werkzeug.utils import secure_filename
            import uuid
            import os
            from datetime import datetime

            safe_filename = secure_filename(
                original_filename
            )

            unique_filename = (
                "student_"
                + str(student["id"])
                + "_"
                + uuid.uuid4().hex
                + "_"
                + safe_filename
            )

            # ------------------------------------------------
            # USE MAIN PROJECT UPLOAD FOLDER
            # ------------------------------------------------

            upload_folder = app.config[
                "UPLOAD_FOLDER"
            ]

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            # ------------------------------------------------
            # COMPLETE FILE PATH
            # ------------------------------------------------

            full_path = os.path.join(
                upload_folder,
                unique_filename
            )

            # ------------------------------------------------
            # SAVE FILE
            # ------------------------------------------------

            try:

                document_file.save(
                    full_path
                )

            except Exception as e:

                print(
                    "STUDENT DOCUMENT UPLOAD ERROR:",
                    repr(e)
                )

                flash(
                    "Unable to upload document.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            # ------------------------------------------------
            # CHECK FILE WAS ACTUALLY SAVED
            # ------------------------------------------------

            if not os.path.exists(full_path):

                flash(
                    "Document file could not be saved.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            # ------------------------------------------------
            # SAVE DOCUMENT INFORMATION IN DATABASE
            # ------------------------------------------------

            upload_date = datetime.now().strftime(
                "%Y-%m-%d"
            )

            try:

                conn.execute("""
                    INSERT INTO documents
                    (
                        student_id,
                        document_type,
                        file_name,
                        file_path,
                        upload_date
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    student["id"],
                    document_type,
                    original_filename,
                    unique_filename,
                    upload_date
                ))

                conn.commit()

            except Exception as e:

                print(
                    "STUDENT DOCUMENT DATABASE ERROR:",
                    repr(e)
                )

                # DELETE FILE IF DATABASE INSERT FAILS
                if os.path.exists(full_path):

                    try:

                        os.remove(
                            full_path
                        )

                    except OSError:
                        pass

                flash(
                    "Unable to save document information.",
                    "error"
                )

                return redirect(
                    url_for("student_documents")
                )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            flash(
                "Document uploaded successfully.",
                "success"
            )

            return redirect(
                url_for("student_documents")
            )

        # ====================================================
        # GET ALL DOCUMENTS OF LOGGED-IN STUDENT
        # ====================================================

        documents = conn.execute("""
            SELECT *
            FROM documents
            WHERE student_id = ?
            ORDER BY id DESC
        """, (
            student["id"],
        )).fetchall()

    finally:

        conn.close()

    # --------------------------------------------------------
    # DISPLAY DOCUMENT PAGE
    # --------------------------------------------------------

    return render_template(
        "student_documents.html",
        student=student,
        documents=documents
    )

# ============================================================
# STUDENT - NOTIFICATIONS
# ============================================================
@app.route("/student/notifications")
def student_notifications():
    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:
        student = conn.execute("""
            SELECT *
            FROM students
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if student is None:
            flash("Student profile is not linked with this login.", "error")
            return redirect(url_for("login"))

        notifications = conn.execute("""
            SELECT *
            FROM notifications
            WHERE target_role IN ('student', 'all')
            ORDER BY id DESC
        """).fetchall()

    finally:
        conn.close()

    return render_template(
        "student_notifications.html",
        student=student,
        notifications=notifications
    )



@app.route(
    "/student/documents/view/<int:document_id>"
)
def student_document_file(document_id):

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        student = conn.execute("""
            SELECT *
            FROM students
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if student is None:
            return redirect(
                url_for("login")
            )

        document = conn.execute("""
            SELECT *
            FROM documents
            WHERE id = ?
            AND student_id = ?
            LIMIT 1
        """, (
            document_id,
            student["id"]
        )).fetchone()

    finally:
        conn.close()

    if document is None:

        flash(
            "Document not found.",
            "error"
        )

        return redirect(
            url_for("student_documents")
        )

    import os
    from flask import send_from_directory

    file_path = document["file_path"]

    # MAIN PROJECT UPLOAD FOLDER
    full_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_path
    )

    if not os.path.exists(full_path):

        # SUPPORT OLD STUDENT UPLOAD PATH
        if os.path.isabs(file_path) and os.path.exists(file_path):
            full_path = file_path

        else:
            flash(
                "Document file is not available.",
                "error"
            )

            return redirect(
                url_for("student_documents")
            )

    return send_from_directory(
        os.path.dirname(full_path),
        os.path.basename(full_path),
        as_attachment=False
    )




@app.route(
    "/student/documents/download/<int:document_id>"
)
def download_student_document(document_id):

    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:

        student = conn.execute("""
            SELECT *
            FROM students
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if student is None:
            return redirect(
                url_for("login")
            )

        document = conn.execute("""
            SELECT *
            FROM documents
            WHERE id = ?
            AND student_id = ?
            LIMIT 1
        """, (
            document_id,
            student["id"]
        )).fetchone()

    finally:
        conn.close()

    if document is None:

        flash(
            "Document not found.",
            "error"
        )

        return redirect(
            url_for("student_documents")
        )

    import os
    from flask import send_from_directory

    file_path = document["file_path"]

    # MAIN PROJECT UPLOAD FOLDER
    full_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_path
    )

    if not os.path.exists(full_path):

        # SUPPORT OLD STUDENT UPLOAD PATH
        if os.path.isabs(file_path) and os.path.exists(file_path):
            full_path = file_path

        else:
            flash(
                "Document file is not available.",
                "error"
            )

            return redirect(
                url_for("student_documents")
            )

    return send_from_directory(
        os.path.dirname(full_path),
        os.path.basename(full_path),
        as_attachment=True,
        download_name=document["file_name"]
    )




# ============================================================
# CREATE STUDENT LOGIN
# ============================================================

@app.route(
    "/admin/students/create-login/<int:student_id>",
    methods=["GET", "POST"]
)
def create_student_login(student_id):

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()

    if student is None:

        conn.close()

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for("view_students")
        )

    # --------------------------------------------------------
    # CHECK IF LOGIN ALREADY EXISTS
    # --------------------------------------------------------

    if student["user_id"]:

        conn.close()

        flash(
            "This student already has a login account.",
            "error"
        )

        return redirect(
            url_for("view_students")
        )


    # --------------------------------------------------------
    # CREATE LOGIN
    # --------------------------------------------------------

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        # Check empty fields

        if not username or not password:

            conn.close()

            return render_template(
                "create_student_login.html",
                student=student,
                error="Username and password are required."
            )


        # Check username already exists

        existing_user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()


        if existing_user:

            conn.close()

            return render_template(
                "create_student_login.html",
                student=student,
                error="This username already exists. Please choose another username."
            )


        # ----------------------------------------------------
        # CREATE USER ACCOUNT
        # ----------------------------------------------------

        cursor = conn.execute("""
            INSERT INTO users
            (
                username,
                password,
                role
            )
            VALUES (?, ?, ?)
        """, (
            username,
            password,
            "student"
        ))


        user_id = cursor.lastrowid


        # ----------------------------------------------------
        # LINK USER WITH STUDENT
        # ----------------------------------------------------

        conn.execute("""
            UPDATE students
            SET user_id = ?
            WHERE id = ?
        """, (
            user_id,
            student_id
        ))


        conn.commit()

        conn.close()


        flash(
            "Student login created successfully.",
            "success"
        )


        return redirect(
            url_for("view_students")
        )


    conn.close()


    return render_template(
        "create_student_login.html",
        student=student
    )

# ============================================================
# FACULTY - NOTIFICATIONS
# ============================================================
@app.route("/faculty/notifications")
def faculty_notifications():
    if not login_required():
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    conn = get_db_connection()

    try:
        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,)).fetchone()

        if faculty is None:
            flash("Faculty profile is not linked with this login.", "error")
            return redirect(url_for("login"))

        notifications = conn.execute("""
            SELECT *
            FROM notifications
            WHERE target_role IN ('faculty', 'all')
            ORDER BY id DESC
        """).fetchall()

    finally:
        conn.close()

    return render_template(
        "faculty_notifications.html",
        faculty=faculty,
        notifications=notifications
    )

@app.route("/admin/faculty/add", methods=["GET", "POST"])
def add_faculty():

    if not admin_required():
        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        designation = request.form.get("designation", "").strip()

        # NEW LOGIN DETAILS
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not name:
            return render_template(
                "add_faculty.html",
                error="Faculty name is required."
            )

        if not username:
            return render_template(
                "add_faculty.html",
                error="Username is required."
            )

        if not password:
            return render_template(
                "add_faculty.html",
                error="Password is required."
            )

        conn = get_db_connection()

        try:

            # ============================================
            # CHECK USERNAME
            # ============================================

            existing_user = conn.execute("""
                SELECT id
                FROM users
                WHERE username = ?
            """, (username,)).fetchone()

            if existing_user:

                return render_template(
                    "add_faculty.html",
                    error="Username already exists. Please choose another username."
                )


            # ============================================
            # CREATE FACULTY LOGIN
            # ============================================

            cursor = conn.execute("""
                INSERT INTO users
                (username, password, role)
                VALUES (?, ?, ?)
            """, (
                username,
                password,
                "faculty"
            ))

            user_id = cursor.lastrowid


            # ============================================
            # CREATE FACULTY
            # ============================================

            conn.execute("""
                INSERT INTO faculty
                (
                    name,
                    email,
                    phone,
                    department,
                    designation,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                phone,
                department,
                designation,
                user_id
            ))


            conn.commit()

            return redirect(
                url_for("view_faculty")
            )

        except Exception as e:

            conn.rollback()

            return render_template(
                "add_faculty.html",
                error=f"Unable to create faculty account: {e}"
            )

        finally:

            conn.close()


    return render_template(
        "add_faculty.html"
    )
@app.route("/admin/faculty/edit/<int:faculty_id>", methods=["GET", "POST"])
def edit_faculty(faculty_id):

    if not admin_required():
        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    faculty = conn.execute(
        "SELECT * FROM faculty WHERE id = ?",
        (faculty_id,)
    ).fetchone()

    if faculty is None:
        conn.close()
        return redirect(
            url_for("view_faculty")
        )

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        designation = request.form.get("designation", "").strip()

        conn.execute("""
            UPDATE faculty
            SET name = ?,
                email = ?,
                phone = ?,
                department = ?,
                designation = ?
            WHERE id = ?
        """, (
            name,
            email,
            phone,
            department,
            designation,
            faculty_id
        ))

        conn.commit()
        conn.close()

        return redirect(
            url_for("view_faculty")
        )

    conn.close()

    return render_template(
        "edit_faculty.html",
        faculty=faculty
    )
@app.route("/admin/faculty/delete/<int:faculty_id>")
def delete_faculty(faculty_id):

    if not admin_required():
        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM faculty WHERE id = ?",
        (faculty_id,)
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("view_faculty")
    )

# ============================================================
# CREATE LOGIN FOR EXISTING FACULTY
# ============================================================

@app.route(
    "/admin/faculty/create-login/<int:faculty_id>",
    methods=["GET", "POST"]
)
def create_faculty_login(faculty_id):

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Get existing faculty
    faculty = conn.execute("""
        SELECT *
        FROM faculty
        WHERE id = ?
    """, (faculty_id,)).fetchone()

    if faculty is None:
        conn.close()
        flash("Faculty not found.", "error")
        return redirect(url_for("view_faculty"))

    # Already has login
    if faculty["user_id"]:
        conn.close()
        flash(
            "This faculty already has a login account.",
            "error"
        )
        return redirect(url_for("view_faculty"))

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if not username or not password:

            conn.close()

            return render_template(
                "create_faculty_login.html",
                faculty=faculty,
                error="Username and password are required."
            )

        # Check username already exists
        existing_user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "create_faculty_login.html",
                faculty=faculty,
                error="This username already exists. Please choose another username."
            )

        # Create user account
        cursor = conn.execute("""
            INSERT INTO users
            (
                username,
                password,
                role
            )
            VALUES (?, ?, ?)
        """, (
            username,
            password,
            "faculty"
        ))

        user_id = cursor.lastrowid

        # Link user account with existing faculty
        conn.execute("""
            UPDATE faculty
            SET user_id = ?
            WHERE id = ?
        """, (
            user_id,
            faculty_id
        ))

        conn.commit()
        conn.close()

        flash(
            "Faculty login created successfully.",
            "success"
        )

        return redirect(
            url_for("view_faculty")
        )

    conn.close()

    return render_template(
        "create_faculty_login.html",
        faculty=faculty
    )


# ============================================================
# ASSIGN COURSE TO FACULTY
# ============================================================

@app.route(
    "/admin/faculty/assign-course/<int:faculty_id>",
    methods=["GET", "POST"]
)
def assign_faculty_course(faculty_id):

    # --------------------------------------------------------
    # ADMIN CHECK
    # --------------------------------------------------------

    if not admin_required():
        return redirect(url_for("login"))


    # --------------------------------------------------------
    # DATABASE CONNECTION
    # --------------------------------------------------------

    conn = get_db_connection()


    # --------------------------------------------------------
    # GET FACULTY
    # --------------------------------------------------------

    faculty = conn.execute("""
        SELECT *
        FROM faculty
        WHERE id = ?
    """, (faculty_id,)).fetchone()


    # Faculty not found
    if faculty is None:

        conn.close()

        return redirect(
            url_for("view_faculty")
        )


    # --------------------------------------------------------
    # POST - ASSIGN COURSE
    # --------------------------------------------------------

    if request.method == "POST":

        course_id = request.form.get(
            "course_id",
            ""
        ).strip()

        academic_year = request.form.get(
            "academic_year",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not course_id:

            conn.close()

            return """
                <script>
                    alert("Please select a course.");
                    window.history.back();
                </script>
            """


        if not academic_year:

            conn.close()

            return """
                <script>
                    alert("Please enter academic year.");
                    window.history.back();
                </script>
            """


        if not semester:

            conn.close()

            return """
                <script>
                    alert("Please select semester.");
                    window.history.back();
                </script>
            """


        # ----------------------------------------------------
        # CHECK COURSE
        # ----------------------------------------------------

        course = conn.execute("""
            SELECT *
            FROM courses
            WHERE id = ?
        """, (course_id,)).fetchone()


        if course is None:

            conn.close()

            return """
                <script>
                    alert("Invalid course selected.");
                    window.history.back();
                </script>
            """


        # ----------------------------------------------------
        # CHECK DUPLICATE ASSIGNMENT
        # ----------------------------------------------------

        existing_assignment = conn.execute("""
            SELECT *
            FROM faculty_courses
            WHERE faculty_id = ?
              AND course_id = ?
              AND academic_year = ?
              AND semester = ?
        """, (
            faculty_id,
            course_id,
            academic_year,
            semester
        )).fetchone()


        if existing_assignment:

            conn.close()

            return """
                <script>
                    alert("This course is already assigned to this faculty for the selected academic year and semester.");
                    window.history.back();
                </script>
            """


        # ----------------------------------------------------
        # ASSIGN COURSE
        # ----------------------------------------------------

        conn.execute("""
            INSERT INTO faculty_courses
            (
                faculty_id,
                course_id,
                academic_year,
                semester
            )
            VALUES (?, ?, ?, ?)
        """, (
            faculty_id,
            course_id,
            academic_year,
            semester
        ))


        conn.commit()


        # ----------------------------------------------------
        # CLOSE DATABASE
        # ----------------------------------------------------

        conn.close()


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return """
            <script>
                alert("Course assigned successfully.");
                window.location.href = "/admin/faculty";
            </script>
        """


    # --------------------------------------------------------
    # GET ALL COURSES
    # --------------------------------------------------------

    courses = conn.execute("""
        SELECT
            id,
            course_name,
            course_code,
            department,
            duration
        FROM courses
        ORDER BY course_name ASC
    """).fetchall()


    # --------------------------------------------------------
    # GET ALREADY ASSIGNED COURSES
    # --------------------------------------------------------

    assigned_courses = conn.execute("""
        SELECT
            faculty_courses.id,
            faculty_courses.academic_year,
            faculty_courses.semester,

            courses.course_name,
            courses.course_code,
            courses.department

        FROM faculty_courses

        INNER JOIN courses
            ON faculty_courses.course_id = courses.id

        WHERE faculty_courses.faculty_id = ?

        ORDER BY
            faculty_courses.academic_year DESC,
            courses.course_name ASC
    """, (faculty_id,)).fetchall()


    # --------------------------------------------------------
    # CLOSE DATABASE
    # --------------------------------------------------------

    conn.close()


    # --------------------------------------------------------
    # DISPLAY PAGE
    # --------------------------------------------------------

    return render_template(
        "assign_faculty_course.html",
        faculty=faculty,
        courses=courses,
        assigned_courses=assigned_courses
    )

# ============================================================
# UNASSIGN FACULTY COURSE
# ============================================================

@app.route(
    "/admin/faculty/unassign-course/<int:assignment_id>"
)
def unassign_faculty_course(assignment_id):

    if not admin_required():
        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    assignment = conn.execute("""
        SELECT id
        FROM faculty_courses
        WHERE id = ?
    """, (assignment_id,)).fetchone()

    if assignment is None:

        conn.close()

        return """
            <script>
                alert("Course assignment not found.");
                window.history.back();
            </script>
        """

    conn.execute("""
        DELETE FROM faculty_courses
        WHERE id = ?
    """, (assignment_id,))

    conn.commit()

    conn.close()

    return """
        <script>
            alert("Course unassigned successfully.");
            window.history.back();
        </script>
    """
# ============================================================
# VIEW FACULTY
# ============================================================

@app.route("/admin/faculty")
def view_faculty():

    if not admin_required():
        return redirect(
            url_for("login")
        )

    search = request.args.get("search", "").strip()

    conn = get_db_connection()

    if search:

        faculty = conn.execute("""
            SELECT *
            FROM faculty
            WHERE name LIKE ?
               OR email LIKE ?
               OR department LIKE ?
               OR designation LIKE ?
               OR phone LIKE ?
            ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()

    else:

        faculty = conn.execute("""
            SELECT *
            FROM faculty
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    return render_template(
        "faculty.html",
        faculty=faculty,
        search=search
    )

# ============================================================
# VIEW COURSES
# ============================================================

@app.route("/admin/courses")
def view_courses():

    if not admin_required():
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()

    conn = get_db_connection()

    if search:
        search_value = f"%{search}%"

        courses = conn.execute("""
            SELECT *
            FROM courses
            WHERE
                course_name LIKE ?
                OR course_code LIKE ?
                OR department LIKE ?
                OR duration LIKE ?
            ORDER BY id DESC
        """, (
            search_value,
            search_value,
            search_value,
            search_value
        )).fetchall()

    else:
        courses = conn.execute("""
            SELECT *
            FROM courses
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    return render_template(
        "courses.html",
        courses=courses,
        search=search
    )

# ============================================================
# ADD COURSE
# ============================================================

@app.route(
    "/admin/courses/add",
    methods=["GET", "POST"]
)
def add_course():

    if not admin_required():

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        course_name = request.form.get(
            "course_name",
            ""
        ).strip()

        course_code = request.form.get(
            "course_code",
            ""
        ).strip()

        department = request.form.get(
            "department",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        if not course_name:

            flash(
                "Course name is required.",
                "error"
            )

            return redirect(
                url_for("add_course")
            )

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO courses
            (
                course_name,
                course_code,
                department,
                duration
            )

            VALUES (?, ?, ?, ?)
        """, (
            course_name,
            course_code,
            department,
            duration
        ))

        conn.commit()

        conn.close()

        flash(
            "Course added successfully.",
            "success"
        )

        return redirect(
            url_for("view_courses")
        )

    return render_template(
        "add_course.html"
    )
# ============================================================
# EDIT COURSE
# ============================================================

@app.route(
    "/admin/courses/edit/<int:course_id>",
    methods=["GET", "POST"]
)
def edit_course(course_id):

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    course = conn.execute("""
        SELECT *
        FROM courses
        WHERE id = ?
    """, (course_id,)).fetchone()

    if not course:
        conn.close()

        flash(
            "Course not found.",
            "error"
        )

        return redirect(
            url_for("view_courses")
        )

    if request.method == "POST":

        course_name = request.form.get(
            "course_name",
            ""
        ).strip()

        course_code = request.form.get(
            "course_code",
            ""
        ).strip()

        department = request.form.get(
            "department",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        if not course_name:

            conn.close()

            flash(
                "Course name is required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_course",
                    course_id=course_id
                )
            )

        conn.execute("""
            UPDATE courses
            SET
                course_name = ?,
                course_code = ?,
                department = ?,
                duration = ?
            WHERE id = ?
        """, (
            course_name,
            course_code,
            department,
            duration,
            course_id
        ))

        conn.commit()
        conn.close()

        flash(
            "Course updated successfully.",
            "success"
        )

        return redirect(
            url_for("view_courses")
        )

    conn.close()

    return render_template(
        "edit_course.html",
        course=course
    )
# ============================================================
# DELETE COURSE
# ============================================================

@app.route(
    "/admin/courses/delete/<int:course_id>"
)
def delete_course(course_id):

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    course = conn.execute("""
        SELECT id
        FROM courses
        WHERE id = ?
    """, (course_id,)).fetchone()

    if not course:
        conn.close()

        flash(
            "Course not found.",
            "error"
        )

        return redirect(
            url_for("view_courses")
        )

    conn.execute("""
        DELETE FROM courses
        WHERE id = ?
    """, (course_id,))

    conn.commit()
    conn.close()

    flash(
        "Course deleted successfully.",
        "success"
    )

    return redirect(
        url_for("view_courses")
    )


# ============================================================
# DOCUMENTS - MAIN PAGE
#
# Student search + documents grouped student-wise
# ============================================================

# ============================================================
# DOCUMENTS - MAIN PAGE
#
# Student search + documents grouped student-wise
# ============================================================
@app.route("/admin/documents")
def view_documents():

    if not admin_required():
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    selected_course = request.args.get("course", "").strip()

    conn = get_db_connection()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    total_documents = conn.execute("""
        SELECT COUNT(*)
        FROM documents
    """).fetchone()[0]

    uploaded_documents = total_documents

    pending_documents = conn.execute("""
        SELECT COUNT(*)
        FROM students s
        WHERE NOT EXISTS (
            SELECT 1
            FROM documents d
            WHERE d.student_id = s.id
        )
    """).fetchone()[0]

    # --------------------------------------------------------
    # COURSES
    # --------------------------------------------------------

    course_rows = conn.execute("""
        SELECT DISTINCT course
        FROM students
        WHERE course IS NOT NULL
        AND course != ''
        ORDER BY course
    """).fetchall()

    courses = [
        row["course"]
        for row in course_rows
    ]

    # --------------------------------------------------------
    # STUDENT QUERY
    # Only students having documents
    # --------------------------------------------------------

    query = """
        SELECT DISTINCT s.*
        FROM students s
        INNER JOIN documents d
            ON d.student_id = s.id
        WHERE 1 = 1
    """

    params = []

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:

        query += """
            AND (
                s.name LIKE ?
                OR s.roll_no LIKE ?
                OR CAST(s.id AS TEXT) LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    # --------------------------------------------------------
    # COURSE FILTER
    # --------------------------------------------------------

    if selected_course:

        query += """
            AND s.course = ?
        """

        params.append(selected_course)

    query += """
        ORDER BY s.name
    """

    student_rows = conn.execute(
        query,
        params
    ).fetchall()

    # --------------------------------------------------------
    # CREATE STUDENT LIST
    # --------------------------------------------------------

    students = []

    for student in student_rows:

        documents = conn.execute("""
            SELECT *
            FROM documents
            WHERE student_id = ?
            ORDER BY id DESC
        """, (
            student["id"],
        )).fetchall()

        # Add student only if documents exist
        if documents:

            students.append({
                "id": student["id"],
                "student_code": student["student_code"],
                "roll_no": student["roll_no"],
                "name": student["name"],
                "course": student["course"],
                "documents": documents
            })

    conn.close()

    # --------------------------------------------------------
    # RETURN PAGE
    # --------------------------------------------------------

    return render_template(
        "documents.html",
        students=students,
        courses=courses,
        search=search,
        selected_course=selected_course,
        total_students=total_students,
        total_documents=total_documents,
        uploaded_documents=uploaded_documents,
        pending_documents=pending_documents
    )

# ============================================================
# DOCUMENTS - ADD / MULTIPLE UPLOAD
# ============================================================

@app.route(
    "/admin/documents/add",
    methods=["GET", "POST"]
)
def add_document():

    if not admin_required():
        return redirect(url_for("login"))

    conn = get_db_connection()

    students = conn.execute("""
        SELECT
            id,
            roll_no,
            name,
            course
        FROM students
        ORDER BY name
    """).fetchall()

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        document_types = request.form.getlist(
            "document_type[]"
        )

        files = request.files.getlist(
            "document_file[]"
        )

        # ----------------------------------------------------
        # VALIDATE STUDENT
        # ----------------------------------------------------

        if not student_id:

            conn.close()

            flash(
                "Please enter a valid student name.",
                "error"
            )

            return redirect(
                url_for("add_document")
            )

        student = conn.execute("""
            SELECT *
            FROM students
            WHERE id = ?
        """, (student_id,)).fetchone()

        if not student:

            conn.close()

            flash(
                "Invalid student.",
                "error"
            )

            return redirect(
                url_for("add_document")
            )

        # ----------------------------------------------------
        # VALIDATE DOCUMENT ROWS
        # ----------------------------------------------------

        if not document_types or not files:

            conn.close()

            flash(
                "Please add at least one document.",
                "error"
            )

            return redirect(
                url_for("add_document")
            )

        uploaded_count = 0

        # ----------------------------------------------------
        # UPLOAD MULTIPLE DOCUMENTS
        # ----------------------------------------------------

        for document_type, file in zip(
            document_types,
            files
        ):

            document_type = document_type.strip()

            # Skip empty rows
            if not document_type:
                continue

            # Check document type
            if document_type not in DOCUMENT_TYPES:
                continue

            # Check file
            if not file or not file.filename:
                continue

            original_name = secure_filename(
                file.filename
            )

            if not original_name:
                continue

            if not allowed_file(original_name):
                continue

            extension = original_name.rsplit(
                ".",
                1
            )[1].lower()

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )

            student_part = (
                f"student_{student['id']}"
            )

            document_part = secure_filename(
                document_type
            )

            saved_name = (
                f"{student_part}_"
                f"{document_part}_"
                f"{timestamp}."
                f"{extension}"
            )

            save_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                saved_name
            )

            file.save(save_path)

            upload_date = datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            )

            conn.execute("""
                INSERT INTO documents
                (
                    student_id,
                    document_type,
                    file_name,
                    file_path,
                    upload_date
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                student["id"],
                document_type,
                original_name,
                saved_name,
                upload_date
            ))

            uploaded_count += 1

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        conn.commit()
        conn.close()

        if uploaded_count == 0:

            flash(
                "No valid documents were uploaded.",
                "error"
            )

            return redirect(
                url_for("add_document")
            )

        flash(
            f"{uploaded_count} document(s) uploaded successfully.",
            "success"
        )

        return redirect(
            url_for("view_documents")
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    conn.close()

    return render_template(
        "add_document.html",
        students=students,
        document_types=DOCUMENT_TYPES
    )
# ============================================================
# DOCUMENT - VIEW FILE
# ============================================================

@app.route(
    "/admin/documents/view/<int:document_id>"
)
def view_document_file(document_id):

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    document = conn.execute("""
        SELECT *
        FROM documents
        WHERE id = ?
    """, (
        document_id,
    )).fetchone()

    conn.close()

    if not document:

        abort(404)

    file_path = document["file_path"]

    if not file_path:

        abort(404)

    full_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_path
    )

    if not os.path.exists(full_path):

        abort(404)

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file_path,
        as_attachment=False
    )


# ============================================================
# DOCUMENT - DOWNLOAD
# ============================================================

@app.route(
    "/admin/documents/download/<int:document_id>"
)
def download_document(document_id):

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    document = conn.execute("""
        SELECT *
        FROM documents
        WHERE id = ?
    """, (
        document_id,
    )).fetchone()

    conn.close()

    if not document:

        abort(404)

    file_path = document["file_path"]

    full_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_path
    )

    if not os.path.exists(full_path):

        abort(404)

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file_path,
        as_attachment=True,
        download_name=document["file_name"]
    )


# ============================================================
# DOCUMENT - EDIT
#
# Only document type can be changed.
# Student and uploaded file remain unchanged.
# ============================================================

@app.route(
    "/admin/documents/edit/<int:document_id>",
    methods=["GET", "POST"]
)
def edit_document(document_id):

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    document = conn.execute("""
        SELECT
            documents.*,
            students.name,
            students.roll_no,
            students.course
        FROM documents

        LEFT JOIN students
        ON documents.student_id = students.id

        WHERE documents.id = ?
    """, (
        document_id,
    )).fetchone()

    if not document:

        conn.close()

        abort(404)

    if request.method == "POST":

        document_type = request.form.get(
            "document_type",
            ""
        ).strip()

        if document_type not in DOCUMENT_TYPES:

            conn.close()

            flash(
                "Please select a valid document type.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_document",
                    document_id=document_id
                )
            )

        conn.execute("""
            UPDATE documents

            SET document_type = ?

            WHERE id = ?
        """, (
            document_type,
            document_id
        ))

        conn.commit()

        conn.close()

        flash(
            "Document updated successfully.",
            "success"
        )

        return redirect(
            url_for("view_documents")
        )

    conn.close()

    return render_template(
        "edit_document.html",
        document=document,
        document_types=DOCUMENT_TYPES
    )


# ============================================================
# DOCUMENT - DELETE
# ============================================================

@app.route(
    "/admin/documents/delete/<int:document_id>"
)
def delete_document(document_id):

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    document = conn.execute("""
        SELECT *
        FROM documents
        WHERE id = ?
    """, (
        document_id,
    )).fetchone()

    if not document:

        conn.close()

        abort(404)

    # --------------------------------------------------------
    # DELETE PHYSICAL FILE
    # --------------------------------------------------------

    file_path = document["file_path"]

    if file_path:

        full_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            file_path
        )

        if os.path.exists(full_path):

            try:

                os.remove(
                    full_path
                )

            except OSError:

                pass

    # --------------------------------------------------------
    # DELETE DATABASE RECORD
    # --------------------------------------------------------

    conn.execute("""
        DELETE FROM documents
        WHERE id = ?
    """, (
        document_id,
    ))

    conn.commit()

    conn.close()

    flash(
        "Document deleted successfully.",
        "success"
    )

    return redirect(
        url_for("view_documents")
    )
@app.route("/admin/documents/delete-student/<int:student_id>", methods=["POST"])
def delete_student_documents(student_id):

    conn = sqlite3.connect("campuscore.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all documents of this student
    cursor.execute("""
        SELECT id, file_path
        FROM documents
        WHERE student_id = ?
    """, (student_id,))

    documents = cursor.fetchall()

    # Delete physical files
    for document in documents:

        file_path = document["file_path"]

        if file_path:
            full_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                file_path
            )

            if os.path.exists(full_path):
                os.remove(full_path)

    # Delete only document records
    cursor.execute("""
        DELETE FROM documents
        WHERE student_id = ?
    """, (student_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("view_documents"))
@app.route("/admin/reports/students")
def student_report():

    if not admin_required():
        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    search = request.args.get("search", "").strip()
    selected_course = request.args.get("course", "").strip()

    query = """
        SELECT
            id,
            student_code,
            roll_no,
            name,
            email,
            phone,
            address,
            course
        FROM students
        WHERE 1=1
    """

    params = []

    # Search by Student ID, Name or Roll No
    if search:
        query += """
            AND (
                student_code LIKE ?
                OR name LIKE ?
                OR roll_no LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    # Course filter
    if selected_course:
        query += """
            AND course = ?
        """

        params.append(selected_course)

    query += """
        ORDER BY id DESC
    """

    students = conn.execute(
        query,
        params
    ).fetchall()


    # Total students
    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]


    # Total courses
    total_courses = conn.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]


    # Course list for filter
    courses = conn.execute("""
        SELECT DISTINCT course
        FROM students
        WHERE course IS NOT NULL
        AND course != ''
        ORDER BY course
    """).fetchall()

    courses = [
        row["course"]
        for row in courses
    ]

    conn.close()


    return render_template(
        "student_report.html",
        students=students,
        total_students=total_students,
        total_courses=total_courses,
        courses=courses,
        search=search,
        selected_course=selected_course
    )
@app.route("/admin/reports/faculty")
def faculty_report():

    if not admin_required():
        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    search = request.args.get("search", "").strip()
    selected_department = request.args.get(
        "department",
        ""
    ).strip()

    query = """
        SELECT
            id,
            name,
            email,
            phone,
            department,
            designation
        FROM faculty
        WHERE 1=1
    """

    params = []

    if search:
        query += """
            AND (
                name LIKE ?
                OR email LIKE ?
                OR phone LIKE ?
                OR department LIKE ?
                OR designation LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if selected_department:
        query += """
            AND department = ?
        """

        params.append(selected_department)

    query += """
        ORDER BY id DESC
    """

    faculty = conn.execute(
        query,
        params
    ).fetchall()

    total_faculty = conn.execute("""
        SELECT COUNT(*)
        FROM faculty
    """).fetchone()[0]

    total_departments = conn.execute("""
        SELECT COUNT(DISTINCT department)
        FROM faculty
        WHERE department IS NOT NULL
        AND department != ''
    """).fetchone()[0]

    departments = conn.execute("""
        SELECT DISTINCT department
        FROM faculty
        WHERE department IS NOT NULL
        AND department != ''
        ORDER BY department
    """).fetchall()

    departments = [
        row["department"]
        for row in departments
    ]

    conn.close()

    return render_template(
        "faculty_report.html",
        faculty=faculty,
        total_faculty=total_faculty,
        total_departments=total_departments,
        departments=departments,
        search=search,
        selected_department=selected_department
    )
@app.route("/admin/reports/courses")
def course_report():

    if not admin_required():
        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    search = request.args.get(
        "search",
        ""
    ).strip()

    selected_department = request.args.get(
        "department",
        ""
    ).strip()


    query = """
        SELECT
            id,
            course_name,
            course_code,
            department,
            duration
        FROM courses
        WHERE 1=1
    """

    params = []


    if search:

        query += """
            AND (
                course_name LIKE ?
                OR course_code LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value
        ])


    if selected_department:

        query += """
            AND department = ?
        """

        params.append(
            selected_department
        )


    query += """
        ORDER BY id DESC
    """


    courses = conn.execute(
        query,
        params
    ).fetchall()


    total_courses = conn.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]


    total_departments = conn.execute("""
        SELECT COUNT(DISTINCT department)
        FROM courses
        WHERE department IS NOT NULL
        AND department != ''
    """).fetchone()[0]


    departments = conn.execute("""
        SELECT DISTINCT department
        FROM courses
        WHERE department IS NOT NULL
        AND department != ''
        ORDER BY department
    """).fetchall()


    departments = [
        row["department"]
        for row in departments
    ]


    conn.close()


    return render_template(
        "course_report.html",
        courses=courses,
        total_courses=total_courses,
        total_departments=total_departments,
        departments=departments,
        search=search,
        selected_department=selected_department
    )
# ============================================================
# REPORTS
# ============================================================

@app.route("/admin/reports")
def reports():

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    total_faculty = conn.execute("""
        SELECT COUNT(*)
        FROM faculty
    """).fetchone()[0]

    total_courses = conn.execute("""
        SELECT COUNT(*)
        FROM courses
    """).fetchone()[0]

    total_documents = conn.execute("""
        SELECT COUNT(*)
        FROM documents
    """).fetchone()[0]

    conn.close()

    return render_template(
        "reports.html",
        total_students=total_students,
        total_faculty=total_faculty,
        total_courses=total_courses,
        total_documents=total_documents
    )

@app.route("/admin/reports/documents")
def document_report():

    if not admin_required():
        return redirect(
            url_for("login")
        )

    conn = get_db_connection()

    search = request.args.get(
        "search",
        ""
    ).strip()

    selected_type = request.args.get(
        "document_type",
        ""
    ).strip()

    query = """
        SELECT
            documents.id,
            students.student_code,
            students.roll_no,
            students.name,
            students.course,
            documents.document_type,
            documents.file_name,
            documents.file_path,
            documents.upload_date
        FROM documents
        INNER JOIN students
            ON documents.student_id = students.id
        WHERE 1=1
    """

    params = []

    if search:
        query += """
            AND (
                students.name LIKE ?
                OR students.roll_no LIKE ?
                OR students.student_code LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    if selected_type:
        query += """
            AND documents.document_type = ?
        """

        params.append(
            selected_type
        )

    query += """
        ORDER BY documents.id DESC
    """

    documents = conn.execute(
        query,
        params
    ).fetchall()

    total_documents = conn.execute("""
        SELECT COUNT(*)
        FROM documents
    """).fetchone()[0]

    students_with_documents = conn.execute("""
        SELECT COUNT(DISTINCT student_id)
        FROM documents
    """).fetchone()[0]

    total_document_types = conn.execute("""
        SELECT COUNT(DISTINCT document_type)
        FROM documents
        WHERE document_type IS NOT NULL
        AND document_type != ''
    """).fetchone()[0]

    document_types = conn.execute("""
        SELECT DISTINCT document_type
        FROM documents
        WHERE document_type IS NOT NULL
        AND document_type != ''
        ORDER BY document_type
    """).fetchall()

    document_types = [
        row["document_type"]
        for row in document_types
    ]

    conn.close()

    return render_template(
        "document_report.html",
        documents=documents,
        total_documents=total_documents,
        students_with_documents=students_with_documents,
        total_document_types=total_document_types,
        document_types=document_types,
        search=search,
        selected_type=selected_type
    )
@app.route("/admin/settings")
def settings():
    return render_template("settings.html")


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    init_db()

    print("")
    print("==========================================")
    print("       CAMPUSCORE APPLICATION")
    print("==========================================")
    print("Server running at:")
    print("http://127.0.0.1:5000")
    print("==========================================")
    print("")

    app.run(
        debug=True
    )