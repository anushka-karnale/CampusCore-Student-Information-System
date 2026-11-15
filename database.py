
import sqlite3


# ============================================================
# DATABASE
# ============================================================

DATABASE = "campuscore.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    conn = get_db_connection()
    cursor = conn.cursor()

    # ========================================================
    # USERS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT NOT NULL

        )
    """)

    # ========================================================
    # DEFAULT ADMIN
    # ========================================================

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role)

        VALUES (?, ?, ?)
    """, (
        "admin",
        "admin123",
        "admin"
    ))

    # ========================================================
    # DEFAULT FACULTY
    # ========================================================

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role)

        VALUES (?, ?, ?)
    """, (
        "faculty",
        "faculty123",
        "faculty"
    ))

    # ========================================================
    # DEFAULT STUDENT
    # ========================================================

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role)

        VALUES (?, ?, ?)
    """, (
        "student",
        "student123",
        "student"
    ))

    # ========================================================
    # STUDENTS
    #
    # student_code = STU001, STU002, STU003...
    # This is the unique Student ID.
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_code TEXT UNIQUE,

            roll_no TEXT NOT NULL,

            name TEXT NOT NULL,

            email TEXT NOT NULL,

            phone TEXT,

            course TEXT NOT NULL,

            semester TEXT,

            address TEXT,

            UNIQUE (roll_no, course)

        )
    """)

    # ========================================================
    # ADD student_code TO OLD STUDENTS TABLE
    # ========================================================

    cursor.execute("PRAGMA table_info(students)")

    student_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "student_code" not in student_columns:

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN student_code TEXT
        """)

    # ========================================================
    # GENERATE STUDENT IDs FOR OLD STUDENTS
    #
    # Existing students will get:
    # STU001
    # STU002
    # STU003
    # ...
    # ========================================================

    old_students = cursor.execute("""
        SELECT id
        FROM students
        WHERE student_code IS NULL
           OR TRIM(student_code) = ''
        ORDER BY id ASC
    """).fetchall()

    for student in old_students:

        student_code = f"STU{student['id']:03d}"

        cursor.execute("""
            UPDATE students
            SET student_code = ?
            WHERE id = ?
        """, (
            student_code,
            student["id"]
        ))

    # ========================================================
    # FACULTY
    # ========================================================

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

    # ========================================================
    # COURSES
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            course_name TEXT NOT NULL,

            course_code TEXT,

            department TEXT,

            duration TEXT

        )
    """)

    # ========================================================
    # DOCUMENTS
    #
    # Documents are connected to students using student_id.
    #
    # student_id points to students.id.
    #
    # Student name, roll no and course are NOT stored here.
    # They are obtained from students table when required.
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER NOT NULL,

            document_type TEXT NOT NULL,

            file_name TEXT NOT NULL,

            file_path TEXT NOT NULL,

            upload_date TEXT,

            FOREIGN KEY (student_id)
            REFERENCES students(id)

        )
    """)

    # ========================================================
    # DOCUMENTS TABLE MIGRATION
    #
    # If old documents table exists without student_id,
    # add student_id column.
    # ========================================================

    cursor.execute("PRAGMA table_info(documents)")

    document_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "student_id" not in document_columns:

        cursor.execute("""
            ALTER TABLE documents
            ADD COLUMN student_id INTEGER
        """)

    # ========================================================
    # REMOVE OLD UNUSED DOCUMENT COLUMNS
    #
    # We do NOT need:
    # student_name
    # roll_no
    # course
    # title
    # description
    #
    # Documents are linked through student_id.
    #
    # SQLite cannot directly DROP columns safely in all
    # versions, so we only use the new structure for new data.
    # ========================================================

    conn.commit()

    conn.close()

    print("====================================")
    print("Database initialized successfully!")
    print("====================================")


# ============================================================
# RUN DATABASE
# ============================================================

if __name__ == "__main__":

    init_db()

