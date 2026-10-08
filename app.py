from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(
    __name__,
    template_folder=r"C:\CyberEvidenceTracker\templates"
)

app.secret_key = "cyber_evidence_secret_key"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cyber_evidence"
}


# =========================
# DATABASE CONNECTION
# =========================

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# =========================
# HOME
# =========================

@app.route("/")
def index():
    return redirect(url_for("login"))


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if len(username) < 3:
            flash("Username must be at least 3 characters.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("register"))

        db = get_db()
        cursor = db.cursor()

        try:

            hashed_password = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users
                (username, email, password)
                VALUES (%s, %s, %s)
                """,
                (
                    username,
                    email,
                    hashed_password
                )
            )

            db.commit()

            flash("Registration successful! Please login.")

            return redirect(url_for("login"))

        except mysql.connector.Error as e:

            db.rollback()

            flash("Registration failed: " + str(e))

        finally:

            cursor.close()
            db.close()

    return render_template("register.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db()

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    cursor = db.cursor(dictionary=True)

    # Total Cases
    cursor.execute(
        "SELECT COUNT(*) AS total FROM cases"
    )

    total_cases = cursor.fetchone()["total"]

    # Total Evidence
    cursor.execute(
        "SELECT COUNT(*) AS total FROM evidence"
    )

    total_evidence = cursor.fetchone()["total"]

    # Total Custody Transfers
    cursor.execute(
        "SELECT COUNT(*) AS total FROM custody_logs"
    )

    total_custody = cursor.fetchone()["total"]

    # Open Cases
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM cases
        WHERE status = 'Open'
        """
    )

    open_cases = cursor.fetchone()["total"]

    # Closed Cases
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM cases
        WHERE status = 'Closed'
        """
    )

    closed_cases = cursor.fetchone()["total"]

    cursor.close()
    db.close()

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Cyber Evidence Chain Tracker
        </title>

    </head>

    <body>

        <h1>
            🔐 Cyber Evidence Chain Tracker
        </h1>

        <h2>
            Welcome, {session["username"]}!
        </h2>

        <p>
            Role:
            <strong>
                {session["role"]}
            </strong>
        </p>

        <hr>

        <h2>
            📊 Dashboard
        </h2>

        <table
            border="1"
            cellpadding="15"
            cellspacing="0"
        >

            <tr>

                <th>
                    📁 Total Cases
                </th>

                <th>
                    🔐 Total Evidence
                </th>

                <th>
                    🔗 Custody Transfers
                </th>

                <th>
                    🟢 Open Cases
                </th>

                <th>
                    🔴 Closed Cases
                </th>

            </tr>

            <tr>

                <td>
                    {total_cases}
                </td>

                <td>
                    {total_evidence}
                </td>

                <td>
                    {total_custody}
                </td>

                <td>
                    {open_cases}
                </td>

                <td>
                    {closed_cases}
                </td>

            </tr>

        </table>

        <hr>

        <h3>
            📂 Project Modules
        </h3>

        <a href="/cases">
            📁 Case Management
        </a>

        <br><br>

        <a href="/add-case">
            ➕ Add New Case
        </a>

        <br><br>

        <a href="/evidence">
            🔐 Evidence Management
        </a>

        <br><br>

        <a href="/add-evidence">
            ➕ Add Evidence
        </a>

        <br><br>

        <a href="/verify-evidence">
            🔎 Hash Verification
        </a>

        <br><br>

        <a href="/custody">
            🔗 Chain of Custody
        </a>

        <br><br>

        <a href="/logout">
            🚪 Logout
        </a>

    </body>

    </html>
    """


# =========================
# CASE MANAGEMENT
# =========================

@app.route("/cases")
def cases():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id,
            case_number,
            title,
            description,
            status,
            created_at
        FROM cases
        ORDER BY id DESC
        """
    )

    cases = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "cases.html",
        cases=cases
    )


# =========================
# ADD CASE
# =========================

@app.route("/add-case", methods=["GET", "POST"])
def add_case():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        case_name = request.form["case_name"].strip()
        description = request.form["description"].strip()
        status = request.form["status"]

        if len(case_name) < 3:

            flash(
                "Case name must be at least 3 characters."
            )

            return redirect(
                url_for("add_case")
            )

        case_number = (
            "CASE-" +
            uuid.uuid4().hex[:8].upper()
        )

        db = get_db()

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO cases
            (
                case_number,
                title,
                description,
                status,
                created_by
            )
            VALUES
            (%s, %s, %s, %s, %s)
            """,
            (
                case_number,
                case_name,
                description,
                status,
                session["user_id"]
            )
        )

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Case created successfully!"
        )

        return redirect(
            url_for("cases")
        )

    return render_template(
        "add_case.html"
    )


# =========================
# EVIDENCE MANAGEMENT
# =========================

@app.route("/evidence")
def evidence():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT

            evidence.id,
            evidence.case_id,

            cases.case_number,
            cases.title,

            evidence.evidence_type,
            evidence.description,
            evidence.file_name,
            evidence.sha256_hash,
            evidence.collected_by,
            evidence.collected_at,
            evidence.created_at

        FROM evidence

        JOIN cases
        ON evidence.case_id = cases.id

        ORDER BY evidence.id DESC
        """
    )

    evidence_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "evidence.html",
        evidence_list=evidence_list
    )


# =========================
# ADD EVIDENCE
# =========================

@app.route(
    "/add-evidence",
    methods=["GET", "POST"]
)
def add_evidence():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            id,
            case_number,
            title
        FROM cases
        ORDER BY id DESC
        """
    )

    cases = cursor.fetchall()

    cursor.close()
    db.close()

    if request.method == "POST":

        case_id = request.form["case_id"]

        evidence_type = (
            request.form["evidence_type"]
            .strip()
        )

        description = (
            request.form["description"]
            .strip()
        )

        file_name = (
            request.form["file_name"]
            .strip()
        )

        sha256_hash = (
            request.form["sha256_hash"]
            .strip()
            .lower()
        )

        collected_by = (
            request.form["collected_by"]
            .strip()
        )

        collected_at = (
            request.form["collected_at"]
        )

        if not case_id:

            flash(
                "Please select a case."
            )

            return redirect(
                url_for("add_evidence")
            )

        if len(evidence_type) < 2:

            flash(
                "Evidence type is required."
            )

            return redirect(
                url_for("add_evidence")
            )

        if len(description) < 3:

            flash(
                "Description is required."
            )

            return redirect(
                url_for("add_evidence")
            )

        if sha256_hash:

            if len(sha256_hash) != 64:

                flash(
                    "SHA-256 hash must contain exactly 64 characters."
                )

                return redirect(
                    url_for("add_evidence")
                )

            try:

                int(
                    sha256_hash,
                    16
                )

            except ValueError:

                flash(
                    "Invalid SHA-256 hash."
                )

                return redirect(
                    url_for("add_evidence")
                )

        db = get_db()

        cursor = db.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO evidence
                (
                    case_id,
                    evidence_type,
                    description,
                    file_name,
                    sha256_hash,
                    collected_by,
                    collected_at
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    case_id,
                    evidence_type,
                    description,
                    file_name,
                    sha256_hash,
                    collected_by,
                    collected_at
                )
            )

            db.commit()

            flash(
                "Evidence added successfully!"
            )

        except mysql.connector.Error as e:

            db.rollback()

            flash(
                "Failed to add evidence: " +
                str(e)
            )

        finally:

            cursor.close()
            db.close()

        return redirect(
            url_for("evidence")
        )

    return render_template(
        "add_evidence.html",
        cases=cases
    )


# =========================
# HASH VERIFICATION
# =========================

@app.route(
    "/verify-evidence",
    methods=["GET", "POST"]
)
def verify_evidence():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT

            evidence.id,
            cases.case_number,
            evidence.file_name,
            evidence.sha256_hash

        FROM evidence

        JOIN cases
        ON evidence.case_id = cases.id

        ORDER BY evidence.id DESC
        """
    )

    evidence_list = cursor.fetchall()

    cursor.close()
    db.close()

    result = None

    if request.method == "POST":

        evidence_id = (
            request.form["evidence_id"]
        )

        entered_hash = (
            request.form["sha256_hash"]
            .strip()
            .lower()
        )

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT sha256_hash
            FROM evidence
            WHERE id = %s
            """,
            (evidence_id,)
        )

        evidence = cursor.fetchone()

        cursor.close()
        db.close()

        if evidence:

            stored_hash = (
                evidence["sha256_hash"] or ""
            ).strip().lower()

            if entered_hash == stored_hash:

                result = (
                    "✅ HASH MATCH - "
                    "Evidence integrity verified."
                )

            else:

                result = (
                    "❌ HASH MISMATCH - "
                    "Evidence may have been modified."
                )

        else:

            result = "Evidence not found."

    return render_template(
        "verify_evidence.html",
        evidence_list=evidence_list,
        result=result
    )


# =========================
# CHAIN OF CUSTODY
# =========================

@app.route(
    "/custody",
    methods=["GET", "POST"]
)
def custody():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    cursor = db.cursor(
        dictionary=True
    )

    # Add custody record
    if request.method == "POST":

        evidence_id = (
            request.form["evidence_id"]
        )

        from_person = (
            request.form["from_person"]
            .strip()
        )

        to_person = (
            request.form["to_person"]
            .strip()
        )

        purpose = (
            request.form["purpose"]
            .strip()
        )

        transferred_at = (
            request.form["transferred_at"]
        )

        if not evidence_id:

            flash(
                "Please select evidence."
            )

            cursor.close()
            db.close()

            return redirect(
                url_for("custody")
            )

        if len(from_person) < 2:

            flash(
                "From Person is required."
            )

            cursor.close()
            db.close()

            return redirect(
                url_for("custody")
            )

        if len(to_person) < 2:

            flash(
                "To Person is required."
            )

            cursor.close()
            db.close()

            return redirect(
                url_for("custody")
            )

        if len(purpose) < 3:

            flash(
                "Transfer purpose is required."
            )

            cursor.close()
            db.close()

            return redirect(
                url_for("custody")
            )

        try:

            cursor.execute(
                """
                INSERT INTO custody_logs
                (
                    evidence_id,
                    from_person,
                    to_person,
                    purpose,
                    transferred_at
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    evidence_id,
                    from_person,
                    to_person,
                    purpose,
                    transferred_at
                )
            )

            db.commit()

            flash(
                "Chain of Custody record added successfully!"
            )

        except mysql.connector.Error as e:

            db.rollback()

            flash(
                "Failed to add custody record: " +
                str(e)
            )

        finally:

            cursor.close()
            db.close()

        return redirect(
            url_for("custody")
        )

    # Evidence list
    cursor.execute(
        """
        SELECT

            evidence.id,
            cases.case_number,
            cases.title,
            evidence.file_name,
            evidence.sha256_hash

        FROM evidence

        JOIN cases
        ON evidence.case_id = cases.id

        ORDER BY evidence.id DESC
        """
    )

    evidence_list = cursor.fetchall()

    # Custody history
    cursor.execute(
        """
        SELECT

            custody_logs.id,
            custody_logs.evidence_id,

            evidence.file_name,

            cases.case_number,
            cases.title,

            custody_logs.from_person,
            custody_logs.to_person,
            custody_logs.purpose,
            custody_logs.transferred_at

        FROM custody_logs

        JOIN evidence
        ON custody_logs.evidence_id = evidence.id

        JOIN cases
        ON evidence.case_id = cases.id

        ORDER BY custody_logs.id DESC
        """
    )

    custody_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "custody.html",
        evidence_list=evidence_list,
        custody_list=custody_list
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":

    app.run(
        debug=True
    )