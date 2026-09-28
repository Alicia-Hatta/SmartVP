from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

app = Flask(__name__)

# Use an environment variable in production.
# The fallback keeps the prototype working on your computer.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-only-key"
)

# Session security
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

DATABASE = "smart_vendor_pay.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_database():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    # Enable foreign-key support
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return redirect("/login")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # Basic validation
        if not username or not password:

            return "Username and password are required."

        connection = get_database()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        connection.close()

        password_valid = False

        if user:

            try:

                password_valid = check_password_hash(
                    user["password"],
                    password
                )

            except ValueError:

                # Handles an old/plain-text password
                # that has not yet been converted.
                password_valid = False

        if password_valid:

            # Clear any previous session information
            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect("/dashboard")

        return "Invalid username or password"

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    # -----------------------------------------------------
    # TOTAL INVOICES
    # -----------------------------------------------------

    total_invoices = connection.execute(
        """
        SELECT COUNT(*)
        FROM invoices
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # PENDING APPROVALS
    # -----------------------------------------------------

    pending_approvals = connection.execute(
        """
        SELECT COUNT(*)
        FROM invoices
        WHERE status = 'Pending'
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # TOTAL INVOICE VALUE
    # -----------------------------------------------------

    total_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # PENDING VALUE
    # -----------------------------------------------------

    pending_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        WHERE status = 'Pending'
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # APPROVED VALUE
    # -----------------------------------------------------

    approved_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        WHERE status = 'Approved'
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # PAID VALUE
    # -----------------------------------------------------

    paid_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        WHERE status = 'Paid'
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # COMPLETED PAYMENTS
    # -----------------------------------------------------

    payments_processed = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # OPEN FRAUD ALERTS
    # -----------------------------------------------------

    fraud_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        """
    ).fetchone()[0]

    connection.close()

    return render_template(
        "dashboard.html",

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        ),

        total_invoices=total_invoices,

        pending_approvals=pending_approvals,

        payments_processed=payments_processed,

        fraud_alerts=fraud_alerts,

        total_invoice_value=float(
            total_invoice_value or 0
        ),

        pending_invoice_value=float(
            pending_invoice_value or 0
        ),

        approved_invoice_value=float(
            approved_invoice_value or 0
        ),

        paid_invoice_value=float(
            paid_invoice_value or 0
        )
    )


# =========================================================
# SUPPLIER MANAGEMENT
# =========================================================

@app.route("/suppliers")
def suppliers():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    suppliers = connection.execute(
        """
        SELECT *
        FROM suppliers
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "suppliers.html",

        suppliers=suppliers,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# ADD SUPPLIER
# =========================================================

@app.route(
    "/suppliers/add",
    methods=["GET", "POST"]
)
def add_supplier():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        bank_name = request.form.get(
            "bank_name",
            ""
        ).strip()

        account_number = request.form.get(
            "account_number",
            ""
        ).strip()

        risk_score = request.form.get(
            "risk_score",
            "0"
        ).strip()

        # Required field
        if not name:

            return "Supplier name is required."

        # Validate risk score
        try:

            risk_score = float(risk_score)

        except ValueError:

            return "Risk score must be a valid number."

        if risk_score < 0 or risk_score > 100:

            return "Risk score must be between 0 and 100."

        connection = get_database()

        try:

            connection.execute(
                """
                INSERT INTO suppliers
                (
                    name,
                    email,
                    phone,
                    bank_name,
                    account_number,
                    risk_score
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    phone,
                    bank_name,
                    account_number,
                    risk_score
                )
            )

            connection.execute(
                """
                INSERT INTO audit_logs
                (
                    user_id,
                    action,
                    timestamp
                )
                VALUES (?, ?, datetime('now'))
                """,
                (
                    session["user_id"],
                    "Added supplier: " + name
                )
            )

            connection.commit()

        except sqlite3.Error as error:

            connection.rollback()

            print(
                "Supplier error:",
                error
            )

            connection.close()

            return "An error occurred while adding the supplier."

        connection.close()

        return redirect("/suppliers")

    return render_template(
        "add_supplier.html",

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# INVOICE MANAGEMENT
# =========================================================

@app.route("/invoices")
def invoices():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    invoices = connection.execute(
        """
        SELECT
            invoices.id,
            invoices.invoice_number,
            invoices.amount,
            invoices.invoice_date,
            invoices.status,
            suppliers.name AS supplier_name

        FROM invoices

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        ORDER BY invoices.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "invoices.html",

        invoices=invoices,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# FRAUD DETECTION ENGINE
# =========================================================

def check_invoice_for_fraud(invoice_id):

    connection = None

    findings = []

    try:

        connection = get_database()

        # -------------------------------------------------
        # GET INVOICE + SUPPLIER
        # -------------------------------------------------

        invoice = connection.execute(
            """
            SELECT
                invoices.id,
                invoices.invoice_number,
                invoices.amount,
                invoices.invoice_date,
                invoices.status,

                suppliers.id AS supplier_id,
                suppliers.name AS supplier_name,
                suppliers.risk_score

            FROM invoices

            LEFT JOIN suppliers
                ON invoices.supplier_id = suppliers.id

            WHERE invoices.id = ?
            """,
            (invoice_id,)
        ).fetchone()

        if invoice is None:

            return findings

        amount = float(
            invoice["amount"] or 0
        )

        supplier_id = invoice["supplier_id"]

        supplier_name = (
            invoice["supplier_name"]
            or "Unknown Supplier"
        )

        risk_score = float(
            invoice["risk_score"] or 0
        )

        # =================================================
        # RULE 1 - DUPLICATE INVOICE NUMBER
        # =================================================

        duplicate = connection.execute(
            """
            SELECT COUNT(*)
            FROM invoices

            WHERE invoice_number = ?
            AND id != ?
            """,
            (
                invoice["invoice_number"],
                invoice_id
            )
        ).fetchone()[0]

        if duplicate > 0:

            findings.append({
                "reason":
                    "Duplicate invoice number detected: "
                    + str(invoice["invoice_number"]),

                "severity": "Critical"
            })

        # =================================================
        # RULE 2 - SAME SUPPLIER + SAME AMOUNT
        # =================================================

        if supplier_id is not None:

            same_amount = connection.execute(
                """
                SELECT COUNT(*)
                FROM invoices

                WHERE supplier_id = ?
                AND amount = ?
                AND id != ?
                """,
                (
                    supplier_id,
                    amount,
                    invoice_id
                )
            ).fetchone()[0]

            if same_amount >= 2:

                findings.append({
                    "reason":
                        f"Supplier '{supplier_name}' has "
                        f"multiple invoices with the same "
                        f"amount of R{amount:,.2f}",

                    "severity": "High"
                })

        # =================================================
        # RULE 3 - SUPPLIER RISK SCORE
        # =================================================

        if risk_score >= 80:

            findings.append({
                "reason":
                    f"Supplier '{supplier_name}' has a "
                    f"very high supplier risk score "
                    f"({risk_score:.0f}/100)",

                "severity": "Critical"
            })

        elif risk_score >= 60:

            findings.append({
                "reason":
                    f"Supplier '{supplier_name}' has a "
                    f"high supplier risk score "
                    f"({risk_score:.0f}/100)",

                "severity": "High"
            })

        # =================================================
        # RULE 4 - UNUSUALLY LARGE INVOICE
        # =================================================

        if supplier_id is not None:

            average_amount = connection.execute(
                """
                SELECT AVG(amount)
                FROM invoices

                WHERE supplier_id = ?
                AND id != ?
                """,
                (
                    supplier_id,
                    invoice_id
                )
            ).fetchone()[0]

            if average_amount:

                average_amount = float(
                    average_amount
                )

                if amount >= average_amount * 3:

                    findings.append({
                        "reason":
                            f"Invoice amount "
                            f"R{amount:,.2f} is significantly "
                            f"higher than the supplier's "
                            f"average invoice of "
                            f"R{average_amount:,.2f}",

                        "severity": "High"
                    })

        # =================================================
        # RULE 5 - MULTIPLE RECENT INVOICES
        # =================================================

        if (
            supplier_id is not None
            and invoice["invoice_date"]
        ):

            recent_invoices = connection.execute(
                """
                SELECT COUNT(*)
                FROM invoices

                WHERE supplier_id = ?

                AND invoice_date >=
                    date(?, '-7 days')

                AND invoice_date <= ?

                AND id != ?
                """,
                (
                    supplier_id,
                    invoice["invoice_date"],
                    invoice["invoice_date"],
                    invoice_id
                )
            ).fetchone()[0]

            if recent_invoices >= 3:

                findings.append({
                    "reason":
                        f"Supplier '{supplier_name}' has "
                        f"submitted {recent_invoices + 1} "
                        f"invoices within a 7-day period",

                    "severity": "Medium"
                })

        # =================================================
        # RULE 6 - PAYMENTS EXCEED INVOICE VALUE
        # =================================================

        payment_total = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM payments

            WHERE invoice_id = ?
            """,
            (invoice_id,)
        ).fetchone()[0]

        payment_total = float(
            payment_total or 0
        )

        if payment_total > amount:

            findings.append({
                "reason":
                    f"Payments of R{payment_total:,.2f} "
                    f"exceed the invoice value of "
                    f"R{amount:,.2f}",

                "severity": "Critical"
            })

        return findings

    except sqlite3.Error as error:

        print(
            "Fraud detection error:",
            error
        )

        return []

    finally:

        if connection:

            connection.close()


# =========================================================
# CREATE FRAUD ALERTS
# =========================================================

def create_fraud_alerts(invoice_id):

    findings = check_invoice_for_fraud(
        invoice_id
    )

    if not findings:

        return 0

    connection = get_database()

    created = 0

    try:

        for finding in findings:

            existing = connection.execute(
                """
                SELECT id
                FROM fraud_alerts

                WHERE invoice_id = ?
                AND reason = ?
                AND status = 'Open'
                """,
                (
                    invoice_id,
                    finding["reason"]
                )
            ).fetchone()

            if existing:

                continue

            connection.execute(
                """
                INSERT INTO fraud_alerts
                (
                    invoice_id,
                    reason,
                    severity,
                    status,
                    created_at
                )

                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (
                    invoice_id,
                    finding["reason"],
                    finding["severity"],
                    "Open"
                )
            )

            created += 1

        connection.commit()

    except sqlite3.Error as error:

        connection.rollback()

        print(
            "Error creating fraud alerts:",
            error
        )

    finally:

        connection.close()

    return created


# =========================================================
# ADD INVOICE
# =========================================================

@app.route(
    "/invoices/add",
    methods=["GET", "POST"]
)
def add_invoice():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    suppliers = connection.execute(
        """
        SELECT id, name
        FROM suppliers
        ORDER BY name
        """
    ).fetchall()

    if request.method == "POST":

        supplier_id = request.form.get(
            "supplier_id",
            ""
        )

        invoice_number = request.form.get(
            "invoice_number",
            ""
        ).strip()

        amount = request.form.get(
            "amount",
            ""
        ).strip()

        invoice_date = request.form.get(
            "invoice_date",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if (
            not supplier_id
            or not invoice_number
            or not amount
            or not invoice_date
        ):

            connection.close()

            return "Please complete all invoice fields."

        try:

            supplier_id = int(
                supplier_id
            )

        except ValueError:

            connection.close()

            return "Invalid supplier."

        try:

            amount = float(
                amount
            )

        except ValueError:

            connection.close()

            return "Invoice amount must be a valid number."

        if amount <= 0:

            connection.close()

            return "Invoice amount must be greater than zero."

        # Check supplier exists
        supplier = connection.execute(
            """
            SELECT id
            FROM suppliers
            WHERE id = ?
            """,
            (supplier_id,)
        ).fetchone()

        if supplier is None:

            connection.close()

            return "Supplier not found."

        try:

            # -------------------------------------------------
            # DUPLICATE INVOICE NUMBER CHECK
            # -------------------------------------------------

            duplicate = connection.execute(
                """
                SELECT id
                FROM invoices
                WHERE invoice_number = ?
                """,
                (invoice_number,)
            ).fetchone()

            if duplicate:

                connection.close()

                return (
                    "An invoice with this invoice number "
                    "already exists."
                )

            # -------------------------------------------------
            # INSERT INVOICE
            # -------------------------------------------------

            cursor = connection.execute(
                """
                INSERT INTO invoices
                (
                    supplier_id,
                    invoice_number,
                    amount,
                    invoice_date,
                    status
                )

                VALUES (?, ?, ?, ?, 'Pending')
                """,
                (
                    supplier_id,
                    invoice_number,
                    amount,
                    invoice_date
                )
            )

            invoice_id = cursor.lastrowid

            # -------------------------------------------------
            # AUDIT LOG
            # -------------------------------------------------

            connection.execute(
                """
                INSERT INTO audit_logs
                (
                    user_id,
                    action,
                    timestamp
                )

                VALUES (?, ?, datetime('now'))
                """,
                (
                    session["user_id"],
                    "Created invoice: "
                    + invoice_number
                )
            )

            connection.commit()

        except sqlite3.Error as error:

            connection.rollback()

            print(
                "Invoice creation error:",
                error
            )

            connection.close()

            return (
                "An error occurred while creating "
                "the invoice."
            )

        connection.close()

        # Automatically check invoice for fraud
        create_fraud_alerts(
            invoice_id
        )

        return redirect("/invoices")

    connection.close()

    return render_template(
        "add_invoice.html",

        suppliers=suppliers,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# VIEW INVOICE
# =========================================================

@app.route(
    "/invoices/<int:invoice_id>"
)
def invoice_details(invoice_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    invoice = connection.execute(
        """
        SELECT
            invoices.*,

            suppliers.name AS supplier_name,
            suppliers.email AS supplier_email,
            suppliers.phone AS supplier_phone

        FROM invoices

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        WHERE invoices.id = ?
        """,
        (invoice_id,)
    ).fetchone()

    connection.close()

    if invoice is None:

        return "Invoice not found"

    return render_template(
        "invoice_details.html",

        invoice=invoice,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# EDIT INVOICE
# =========================================================

@app.route(
    "/invoices/<int:invoice_id>/edit",
    methods=["GET", "POST"]
)
def edit_invoice(invoice_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    invoice = connection.execute(
        """
        SELECT *
        FROM invoices
        WHERE id = ?
        """,
        (invoice_id,)
    ).fetchone()

    suppliers = connection.execute(
        """
        SELECT id, name
        FROM suppliers
        ORDER BY name
        """
    ).fetchall()

    if invoice is None:

        connection.close()

        return "Invoice not found"

    if request.method == "POST":

        supplier_id = request.form.get(
            "supplier_id",
            ""
        )

        invoice_number = request.form.get(
            "invoice_number",
            ""
        ).strip()

        amount = request.form.get(
            "amount",
            ""
        ).strip()

        invoice_date = request.form.get(
            "invoice_date",
            ""
        ).strip()

        if (
            not supplier_id
            or not invoice_number
            or not amount
            or not invoice_date
        ):

            connection.close()

            return "Please complete all invoice fields."

        try:

            supplier_id = int(
                supplier_id
            )

        except ValueError:

            connection.close()

            return "Invalid supplier."

        try:

            amount = float(
                amount
            )

        except ValueError:

            connection.close()

            return "Invoice amount must be a valid number."

        if amount <= 0:

            connection.close()

            return "Invoice amount must be greater than zero."

        supplier = connection.execute(
            """
            SELECT id
            FROM suppliers
            WHERE id = ?
            """,
            (supplier_id,)
        ).fetchone()

        if supplier is None:

            connection.close()

            return "Supplier not found."

        duplicate = connection.execute(
            """
            SELECT id
            FROM invoices

            WHERE invoice_number = ?
            AND id != ?
            """,
            (
                invoice_number,
                invoice_id
            )
        ).fetchone()

        if duplicate:

            connection.close()

            return (
                "Another invoice already uses "
                "this invoice number."
            )

        try:

            connection.execute(
                """
                UPDATE invoices

                SET
                    supplier_id = ?,
                    invoice_number = ?,
                    amount = ?,
                    invoice_date = ?

                WHERE id = ?
                """,
                (
                    supplier_id,
                    invoice_number,
                    amount,
                    invoice_date,
                    invoice_id
                )
            )

            connection.execute(
                """
                INSERT INTO audit_logs
                (
                    user_id,
                    action,
                    timestamp
                )

                VALUES (?, ?, datetime('now'))
                """,
                (
                    session["user_id"],
                    "Edited invoice: "
                    + invoice_number
                )
            )

            connection.commit()

        except sqlite3.Error as error:

            connection.rollback()

            print(
                "Invoice edit error:",
                error
            )

            connection.close()

            return (
                "An error occurred while editing "
                "the invoice."
            )

        connection.close()

        # Re-check edited invoice
        create_fraud_alerts(
            invoice_id
        )

        return redirect(
            f"/invoices/{invoice_id}"
        )

    connection.close()

    return render_template(
        "edit_invoice.html",

        invoice=invoice,

        suppliers=suppliers,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# DELETE INVOICE
# =========================================================

@app.route(
    "/invoices/<int:invoice_id>/delete",
    methods=["POST"]
)
def delete_invoice(invoice_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    invoice = connection.execute(
        """
        SELECT invoice_number
        FROM invoices
        WHERE id = ?
        """,
        (invoice_id,)
    ).fetchone()

    if invoice is None:

        connection.close()

        return "Invoice not found."

    # Do not delete invoices that already have payments
    payment_exists = connection.execute(
        """
        SELECT id
        FROM payments
        WHERE invoice_id = ?
        LIMIT 1
        """,
        (invoice_id,)
    ).fetchone()

    if payment_exists:

        connection.close()

        return (
            "This invoice cannot be deleted because "
            "it already has payment records."
        )

    try:

        connection.execute(
            """
            DELETE FROM fraud_alerts
            WHERE invoice_id = ?
            """,
            (invoice_id,)
        )

        connection.execute(
            """
            DELETE FROM invoices
            WHERE id = ?
            """,
            (invoice_id,)
        )

        connection.execute(
            """
            INSERT INTO audit_logs
            (
                user_id,
                action,
                timestamp
            )

            VALUES (?, ?, datetime('now'))
            """,
            (
                session["user_id"],
                "Deleted invoice: "
                + str(invoice["invoice_number"])
            )
        )

        connection.commit()

    except sqlite3.Error as error:

        connection.rollback()

        print(
            "Invoice deletion error:",
            error
        )

        connection.close()

        return (
            "An error occurred while deleting "
            "the invoice."
        )

    connection.close()

    return redirect("/invoices")


# =========================================================
# UPDATE INVOICE STATUS
# =========================================================

@app.route(
    "/invoices/<int:invoice_id>/status",
    methods=["POST"]
)
def update_invoice_status(invoice_id):

    if "user_id" not in session:
        return redirect("/login")

    status = request.form.get(
        "status"
    )

    allowed_statuses = [
        "Pending",
        "Approved",
        "Paid",
        "Rejected"
    ]

    if status not in allowed_statuses:

        return "Invalid invoice status"

    connection = get_database()

    invoice = connection.execute(
        """
        SELECT invoice_number
        FROM invoices
        WHERE id = ?
        """,
        (invoice_id,)
    ).fetchone()

    if invoice is None:

        connection.close()

        return "Invoice not found."

    try:

        connection.execute(
            """
            UPDATE invoices
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                invoice_id
            )
        )

        connection.execute(
            """
            INSERT INTO audit_logs
            (
                user_id,
                action,
                timestamp
            )

            VALUES (?, ?, datetime('now'))
            """,
            (
                session["user_id"],
                "Changed invoice "
                + str(invoice["invoice_number"])
                + " status to "
                + status
            )
        )

        connection.commit()

    except sqlite3.Error as error:

        connection.rollback()

        print(
            "Invoice status error:",
            error
        )

        connection.close()

        return "Unable to update invoice status."

    connection.close()

    return redirect(
        f"/invoices/{invoice_id}"
    )


# =========================================================
# INVOICE VERIFICATION
# =========================================================

@app.route("/invoice-verification")
def invoice_verification():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    invoices = connection.execute(
        """
        SELECT
            invoices.id,
            invoices.invoice_number,
            invoices.amount,
            invoices.invoice_date,
            invoices.status,

            suppliers.name AS supplier_name,

            COUNT(
                CASE
                    WHEN fraud_alerts.status = 'Open'
                    THEN 1
                END
            ) AS open_alerts,

            MAX(
                CASE
                    WHEN fraud_alerts.status = 'Open'
                    THEN fraud_alerts.severity
                END
            ) AS severity

        FROM invoices

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        LEFT JOIN fraud_alerts
            ON invoices.id = fraud_alerts.invoice_id

        GROUP BY
            invoices.id,
            invoices.invoice_number,
            invoices.amount,
            invoices.invoice_date,
            invoices.status,
            suppliers.name

        ORDER BY invoices.id DESC
        """
    ).fetchall()

    total_invoices = len(
        invoices
    )

    verified_count = 0
    review_count = 0
    fraud_count = 0
    pending_count = 0

    verification_data = []

    for invoice in invoices:

        open_alerts = (
            invoice["open_alerts"]
            or 0
        )

        severity = invoice["severity"]

        # -------------------------------------------------
        # FRAUD ALERT
        # -------------------------------------------------

        if (
            open_alerts > 0
            and severity == "Critical"
        ):

            verification_status = "Fraud Alert"

            verification_class = "fraud"

            fraud_count += 1

        # -------------------------------------------------
        # REVIEW
        # -------------------------------------------------

        elif open_alerts > 0:

            verification_status = "Requires Review"

            verification_class = "review"

            review_count += 1

        # -------------------------------------------------
        # REJECTED
        # -------------------------------------------------

        elif invoice["status"] == "Rejected":

            verification_status = "Rejected"

            verification_class = "fraud"

            review_count += 1

        # -------------------------------------------------
        # PENDING
        # -------------------------------------------------

        elif invoice["status"] == "Pending":

            verification_status = "Pending Verification"

            verification_class = "pending"

            pending_count += 1

        # -------------------------------------------------
        # VERIFIED
        # -------------------------------------------------

        else:

            verification_status = "Verified"

            verification_class = "verified"

            verified_count += 1

        verification_data.append({

            "id":
                invoice["id"],

            "invoice_number":
                invoice["invoice_number"],

            "supplier_name":
                (
                    invoice["supplier_name"]
                    or "Unknown Supplier"
                ),

            "amount":
                float(
                    invoice["amount"] or 0
                ),

            "invoice_date":
                invoice["invoice_date"],

            "status":
                invoice["status"],

            "verification_status":
                verification_status,

            "verification_class":
                verification_class
        })

    connection.close()

    return render_template(
        "invoice_verification.html",

        invoices=verification_data,

        total_invoices=total_invoices,

        verified_count=verified_count,

        review_count=review_count,

        fraud_count=fraud_count,

        pending_count=pending_count,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# PAYMENT MANAGEMENT
# =========================================================

@app.route("/payments")
def payments():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    payments = connection.execute(
        """
        SELECT
            payments.id,
            payments.amount,
            payments.payment_date,
            payments.status,

            invoices.invoice_number,

            suppliers.name AS supplier_name

        FROM payments

        LEFT JOIN invoices
            ON payments.invoice_id = invoices.id

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        ORDER BY payments.id DESC
        """
    ).fetchall()

    total_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        """
    ).fetchone()[0]

    completed_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    total_paid = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    connection.close()

    return render_template(
        "payments.html",

        payments=payments,

        total_payments=total_payments,

        completed_payments=completed_payments,

        total_paid=float(
            total_paid or 0
        ),

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# ANALYTICS
# =========================================================

@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect("/login")

    connection = None

    try:

        connection = get_database()

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        total_invoices = connection.execute(
            """
            SELECT COUNT(*)
            FROM invoices
            """
        ).fetchone()[0] or 0

        total_invoice_value = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM invoices
            """
        ).fetchone()[0] or 0

        paid_value = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM invoices
            WHERE status = 'Paid'
            """
        ).fetchone()[0] or 0

        outstanding_value = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM invoices
            WHERE status IN
            (
                'Pending',
                'Approved'
            )
            """
        ).fetchone()[0] or 0

        # -------------------------------------------------
        # MONTHLY EXPENDITURE
        # -------------------------------------------------

        monthly_rows = connection.execute(
            """
            SELECT
                substr(invoice_date, 1, 7) AS month,
                COALESCE(SUM(amount), 0) AS total

            FROM invoices

            WHERE invoice_date IS NOT NULL
            AND TRIM(invoice_date) != ''

            GROUP BY
                substr(invoice_date, 1, 7)

            ORDER BY month ASC
            """
        ).fetchall()

        monthly_data = []

        for row in monthly_rows:

            monthly_data.append({
                "month":
                    row["month"],

                "total":
                    float(
                        row["total"] or 0
                    )
            })

        # -------------------------------------------------
        # SPENDING BY SUPPLIER
        # -------------------------------------------------

        supplier_rows = connection.execute(
            """
            SELECT

                COALESCE(
                    suppliers.name,
                    'Unknown Supplier'
                ) AS supplier_name,

                COALESCE(
                    SUM(invoices.amount),
                    0
                ) AS total

            FROM invoices

            LEFT JOIN suppliers
                ON invoices.supplier_id =
                   suppliers.id

            GROUP BY
                suppliers.id,
                suppliers.name

            ORDER BY total DESC
            """
        ).fetchall()

        supplier_data = []

        for row in supplier_rows:

            supplier_data.append({
                "supplier_name":
                    row["supplier_name"],

                "total":
                    float(
                        row["total"] or 0
                    )
            })

        # -------------------------------------------------
        # INVOICE STATUS
        # -------------------------------------------------

        status_rows = connection.execute(
            """
            SELECT
                COALESCE(
                    status,
                    'Unknown'
                ) AS status,

                COUNT(*) AS total

            FROM invoices

            GROUP BY status

            ORDER BY total DESC
            """
        ).fetchall()

        status_data = []

        for row in status_rows:

            status_data.append({
                "status":
                    row["status"],

                "total":
                    int(
                        row["total"] or 0
                    )
            })

        return render_template(
            "analytics.html",

            username=session.get(
                "username",
                ""
            ),

            role=session.get(
                "role",
                ""
            ),

            total_invoices=
                total_invoices,

            total_invoice_value=
                float(
                    total_invoice_value
                ),

            paid_value=
                float(
                    paid_value
                ),

            outstanding_value=
                float(
                    outstanding_value
                ),

            monthly_data=
                monthly_data,

            supplier_data=
                supplier_data,

            status_data=
                status_data
        )

    except sqlite3.Error as error:

        print(
            "Analytics database error:",
            error
        )

        return (
            "An error occurred while "
            "loading analytics.",
            500
        )

    finally:

        if connection:

            connection.close()


# =========================================================
# FRAUD ALERTS
# =========================================================

@app.route("/fraud-alerts")
def fraud_alerts():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    alerts = connection.execute(
        """
        SELECT
            fraud_alerts.id,
            fraud_alerts.invoice_id,
            fraud_alerts.reason,
            fraud_alerts.severity,
            fraud_alerts.status,
            fraud_alerts.created_at,

            invoices.invoice_number,
            invoices.amount,

            suppliers.name AS supplier_name

        FROM fraud_alerts

        LEFT JOIN invoices
            ON fraud_alerts.invoice_id =
               invoices.id

        LEFT JOIN suppliers
            ON invoices.supplier_id =
               suppliers.id

        ORDER BY fraud_alerts.id DESC
        """
    ).fetchall()

    total_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        """
    ).fetchone()[0]

    open_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        """
    ).fetchone()[0]

    critical_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        AND severity = 'Critical'
        """
    ).fetchone()[0]

    high_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        AND severity = 'High'
        """
    ).fetchone()[0]

    medium_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        AND severity = 'Medium'
        """
    ).fetchone()[0]

    connection.close()

    return render_template(
        "fraud_alerts.html",

        alerts=alerts,

        total_alerts=total_alerts,

        open_alerts=open_alerts,

        critical_alerts=critical_alerts,

        high_alerts=high_alerts,

        medium_alerts=medium_alerts,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# UPDATE FRAUD ALERT STATUS
# =========================================================

@app.route(
    "/fraud-alerts/<int:alert_id>/status",
    methods=["POST"]
)
def update_fraud_alert_status(alert_id):

    if "user_id" not in session:
        return redirect("/login")

    status = request.form.get(
        "status"
    )

    allowed_statuses = [
        "Open",
        "Reviewed",
        "Resolved"
    ]

    if status not in allowed_statuses:

        return "Invalid fraud alert status"

    connection = get_database()

    alert = connection.execute(
        """
        SELECT id
        FROM fraud_alerts
        WHERE id = ?
        """,
        (alert_id,)
    ).fetchone()

    if alert is None:

        connection.close()

        return "Fraud alert not found."

    try:

        connection.execute(
            """
            UPDATE fraud_alerts

            SET status = ?

            WHERE id = ?
            """,
            (
                status,
                alert_id
            )
        )

        connection.execute(
            """
            INSERT INTO audit_logs
            (
                user_id,
                action,
                timestamp
            )

            VALUES (?, ?, datetime('now'))
            """,
            (
                session["user_id"],
                "Updated fraud alert "
                + str(alert_id)
                + " to "
                + status
            )
        )

        connection.commit()

    except sqlite3.Error as error:

        connection.rollback()

        print(
            "Fraud alert update error:",
            error
        )

        connection.close()

        return "Unable to update fraud alert."

    connection.close()

    return redirect("/fraud-alerts")


# =========================================================
# AI ASSISTANT
# =========================================================

@app.route(
    "/ai-assistant",
    methods=["GET", "POST"]
)
def ai_assistant():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    # -----------------------------------------------------
    # INVOICE INFORMATION
    # -----------------------------------------------------

    total_invoices = connection.execute(
        """
        SELECT COUNT(*)
        FROM invoices
        """
    ).fetchone()[0]

    total_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        """
    ).fetchone()[0]

    paid_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        WHERE LOWER(status) = 'paid'
        """
    ).fetchone()[0]

    outstanding_value = (
        float(total_value or 0)
        - float(paid_value or 0)
    )

    # -----------------------------------------------------
    # SUPPLIERS
    # -----------------------------------------------------

    supplier_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM suppliers
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # FRAUD ALERTS
    # -----------------------------------------------------

    open_fraud_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        """
    ).fetchone()[0]

    critical_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        AND severity = 'Critical'
        """
    ).fetchone()[0]

    high_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        AND severity = 'High'
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # AI INSIGHTS
    # -----------------------------------------------------

    insights = []

    if total_invoices == 0:

        insights.append(
            "There are currently no invoices "
            "available for analysis."
        )

    else:

        insights.append(
            f"The system is currently monitoring "
            f"{total_invoices} invoice(s) with a "
            f"total value of "
            f"R {float(total_value):,.2f}."
        )

    if outstanding_value > 0:

        insights.append(
            f"Outstanding invoice value is "
            f"R {outstanding_value:,.2f}. "
            f"These invoices should be reviewed "
            f"for payment."
        )

    else:

        insights.append(
            "There is currently no outstanding "
            "invoice value."
        )

    if open_fraud_alerts > 0:

        insights.append(
            f"There are {open_fraud_alerts} "
            f"open fraud alert(s) that require "
            f"review."
        )

    else:

        insights.append(
            "No open fraud alerts are currently "
            "recorded."
        )

    # -----------------------------------------------------
    # AI RECOMMENDATIONS
    # -----------------------------------------------------

    recommendations = []

    if outstanding_value > 0:

        recommendations.append(
            "Review outstanding invoices and "
            "prioritise payments according to "
            "their due dates."
        )

    if critical_alerts > 0:

        recommendations.append(
            "Review critical fraud alerts before "
            "approving payments related to those "
            "invoices."
        )

    if high_alerts > 0:

        recommendations.append(
            "Review high-severity fraud alerts "
            "before processing related payments."
        )

    if supplier_count == 0:

        recommendations.append(
            "Add suppliers to the system so invoice "
            "activity can be linked to supplier "
            "records."
        )

    if not recommendations:

        recommendations.append(
            "Continue monitoring invoice activity "
            "and supplier transactions regularly."
        )

    # -----------------------------------------------------
    # ASK THE AI
    # -----------------------------------------------------

    answer = None

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        ).strip().lower()

        if not question:

            answer = "Please enter a question."

        elif (
            "invoice" in question
            or "invoices" in question
        ):

            answer = (
                f"Smart Vendor Pay currently has "
                f"{total_invoices} invoice(s), "
                f"with a combined value of "
                f"R {float(total_value):,.2f}."
            )

        elif (
            "outstanding" in question
            or "owe" in question
        ):

            answer = (
                f"The current outstanding "
                f"invoice value is "
                f"R {outstanding_value:,.2f}."
            )

        elif (
            "paid" in question
            or "payment" in question
        ):

            answer = (
                f"The total value of paid "
                f"invoices is "
                f"R {float(paid_value):,.2f}. "
                f"The outstanding value is "
                f"R {outstanding_value:,.2f}."
            )

        elif (
            "fraud" in question
            or "alert" in question
            or "alerts" in question
        ):

            if open_fraud_alerts > 0:

                answer = (
                    f"There are currently "
                    f"{open_fraud_alerts} open "
                    f"fraud alert(s). "

                    f"{critical_alerts} are marked "
                    f"Critical and "

                    f"{high_alerts} are marked "
                    f"High. "

                    "Please review the Fraud Alerts "
                    "page before approving related "
                    "payments."
                )

            else:

                answer = (
                    "There are currently no open "
                    "fraud alerts."
                )

        elif "supplier" in question:

            answer = (
                f"There are currently "
                f"{supplier_count} supplier(s) "
                "registered in Smart Vendor Pay."
            )

        elif "summary" in question:

            answer = (
                f"Financial summary: "
                f"{total_invoices} invoice(s), "

                f"R {float(total_value):,.2f} "
                f"total invoice value, "

                f"R {float(paid_value):,.2f} paid, "

                f"R {outstanding_value:,.2f} "
                f"outstanding, "

                f"and {open_fraud_alerts} "
                f"open fraud alert(s)."
            )

        else:

            answer = (
                "I can help you analyse invoices, "
                "payments, suppliers and fraud "
                "alerts. Try asking: "

                "'How many invoices do we have?', "

                "'How much is outstanding?', "

                "'Are there any fraud alerts?', "

                "'How much has been paid?', or "

                "'Give me a financial summary.'"
            )

    connection.close()

    return render_template(
        "ai_assistant.html",

        total_invoices=
            total_invoices,

        total_value=
            float(
                total_value or 0
            ),

        paid_value=
            float(
                paid_value or 0
            ),

        outstanding_value=
            outstanding_value,

        supplier_count=
            supplier_count,

        open_fraud_alerts=
            open_fraud_alerts,

        critical_alerts=
            critical_alerts,

        high_alerts=
            high_alerts,

        insights=
            insights,

        recommendations=
            recommendations,

        answer=
            answer,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "notifications.html",

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# PAYMENT TRACKING
# =========================================================

@app.route("/payment-tracking")
def payment_tracking():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    # -----------------------------------------------------
    # GET PAYMENT RECORDS
    # -----------------------------------------------------

    payments_data = connection.execute(
        """
        SELECT
            payments.id,
            payments.amount,
            payments.payment_date,
            payments.status,

            invoices.id AS invoice_id,
            invoices.invoice_number,
            invoices.amount AS invoice_amount,
            invoices.status AS invoice_status,

            suppliers.name AS supplier_name

        FROM payments

        LEFT JOIN invoices
            ON payments.invoice_id = invoices.id

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        ORDER BY payments.id DESC
        """
    ).fetchall()

    # -----------------------------------------------------
    # PAYMENT STATISTICS
    # -----------------------------------------------------

    total_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        """
    ).fetchone()[0]

    completed_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    pending_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status != 'Completed'
        """
    ).fetchone()[0]

    total_paid = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    total_payment_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # PREPARE TRACKING DATA
    # -----------------------------------------------------

    tracking_data = []

    for payment in payments_data:

        invoice_amount = float(
            payment["invoice_amount"]
            or 0
        )

        payment_amount = float(
            payment["amount"]
            or 0
        )

        if invoice_amount > 0:

            percentage = (
                payment_amount
                / invoice_amount
            ) * 100

        else:

            percentage = 0

        if percentage > 100:

            percentage = 100

        tracking_data.append({

            "id":
                payment["id"],

            "invoice_id":
                payment["invoice_id"],

            "invoice_number":
                (
                    payment["invoice_number"]
                    or "Unknown Invoice"
                ),

            "supplier_name":
                (
                    payment["supplier_name"]
                    or "Unknown Supplier"
                ),

            "payment_amount":
                payment_amount,

            "invoice_amount":
                invoice_amount,

            "payment_date":
                (
                    payment["payment_date"]
                    or "Not Available"
                ),

            "status":
                (
                    payment["status"]
                    or "Unknown"
                ),

            "invoice_status":
                (
                    payment["invoice_status"]
                    or "Unknown"
                ),

            "percentage":
                round(
                    percentage,
                    1
                )
        })

    connection.close()

    return render_template(
        "payment_tracking.html",

        payments=tracking_data,

        total_payments=
            total_payments,

        completed_payments=
            completed_payments,

        pending_payments=
            pending_payments,

        total_paid=
            float(
                total_paid or 0
            ),

        total_payment_value=
            float(
                total_payment_value or 0
            ),

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# PAYMENT HISTORY
# =========================================================

@app.route("/payment-history")
def payment_history():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    history = connection.execute(
        """
        SELECT
            payments.id,
            payments.amount,
            payments.payment_date,
            payments.status,

            invoices.invoice_number,
            invoices.amount AS invoice_amount,

            suppliers.name AS supplier_name

        FROM payments

        LEFT JOIN invoices
            ON payments.invoice_id = invoices.id

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        ORDER BY
            payments.payment_date DESC,
            payments.id DESC
        """
    ).fetchall()

    total_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        """
    ).fetchone()[0]

    completed_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    total_completed_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    connection.close()

    return render_template(
        "payment_history.html",

        payments=history,

        total_payments=
            total_payments,

        completed_payments=
            completed_payments,

        total_completed_value=
            float(
                total_completed_value or 0
            ),

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# PAYMENT APPROVAL
# =========================================================

@app.route("/payment-approval")
def payment_approval():

    if "user_id" not in session:
        return redirect("/login")

    # -----------------------------------------------------
    # ROLE SECURITY
    # -----------------------------------------------------

    if session.get("role") != "Finance Manager":

        return (
            "Access denied. You do not have permission "
            "to approve payments."
        ), 403

    connection = get_database()

    payments = connection.execute(
        """
        SELECT
            payments.id,
            payments.amount,
            payments.payment_date,
            payments.status,

            invoices.id AS invoice_id,
            invoices.invoice_number,
            invoices.amount AS invoice_amount,
            invoices.invoice_date,

            suppliers.name AS supplier_name

        FROM payments

        LEFT JOIN invoices
            ON payments.invoice_id = invoices.id

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        WHERE payments.status = 'Pending'

        ORDER BY payments.id DESC
        """
    ).fetchall()

    pending_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Pending'
        """
    ).fetchone()[0]

    pending_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE status = 'Pending'
        """
    ).fetchone()[0]

    connection.close()

    return render_template(
        "payment_approval.html",

        payments=payments,

        pending_count=
            pending_count,

        pending_value=
            float(
                pending_value or 0
            ),

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# PROCESS PAYMENT APPROVAL
# =========================================================

@app.route(
    "/payment-approval/<int:payment_id>/<action>",
    methods=["POST"]
)
def process_payment_approval(
    payment_id,
    action
):

    if "user_id" not in session:
        return redirect("/login")

    # -----------------------------------------------------
    # ROLE SECURITY
    # -----------------------------------------------------

    if session.get("role") != "Finance Manager":

        return (
            "Access denied. You do not have permission "
            "to approve payments."
        ), 403

    # -----------------------------------------------------
    # ACTION SECURITY
    # -----------------------------------------------------

    if action not in [
        "approve",
        "reject"
    ]:

        return redirect(
            "/payment-approval"
        )

    connection = get_database()

    # -----------------------------------------------------
    # FIND PAYMENT
    # -----------------------------------------------------

    payment = connection.execute(
        """
        SELECT
            id,
            invoice_id,
            amount,
            status

        FROM payments

        WHERE id = ?
        """,
        (payment_id,)
    ).fetchone()

    if payment is None:

        connection.close()

        return redirect(
            "/payment-approval"
        )

    # -----------------------------------------------------
    # ONLY PENDING PAYMENTS
    # -----------------------------------------------------

    if payment["status"] != "Pending":

        connection.close()

        return redirect(
            "/payment-approval"
        )

    # -----------------------------------------------------
    # GET INVOICE
    # -----------------------------------------------------

    invoice = connection.execute(
        """
        SELECT
            id,
            invoice_number,
            amount,
            status

        FROM invoices

        WHERE id = ?
        """,
        (
            payment["invoice_id"],
        )
    ).fetchone()

    if invoice is None:

        connection.close()

        return redirect(
            "/payment-approval"
        )

    # =====================================================
    # APPROVE PAYMENT
    # =====================================================

    if action == "approve":

        # -------------------------------------------------
        # CALCULATE EXISTING COMPLETED PAYMENTS
        # -------------------------------------------------

        existing_completed = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)

            FROM payments

            WHERE invoice_id = ?

            AND status = 'Completed'

            AND id != ?
            """,
            (
                payment["invoice_id"],
                payment_id
            )
        ).fetchone()[0]

        existing_completed = float(
            existing_completed or 0
        )

        payment_amount = float(
            payment["amount"] or 0
        )

        invoice_amount = float(
            invoice["amount"] or 0
        )

        total_after_payment = (
            existing_completed
            + payment_amount
        )

        # -------------------------------------------------
        # SECURITY:
        # PAYMENT CANNOT EXCEED REMAINING INVOICE VALUE
        # -------------------------------------------------

        if total_after_payment > invoice_amount:

            connection.close()

            return (
                "Payment cannot be approved because "
                "the total completed payments would "
                "exceed the invoice amount."
            ), 400

        new_status = "Completed"

        audit_action = (
            "Approved payment "
            + str(payment_id)
            + " for invoice "
            + str(invoice["invoice_number"])
        )

        # -------------------------------------------------
        # UPDATE PAYMENT
        # -------------------------------------------------

        connection.execute(
            """
            UPDATE payments

            SET status = ?

            WHERE id = ?
            """,
            (
                new_status,
                payment_id
            )
        )

        # -------------------------------------------------
        # UPDATE INVOICE IF FULLY PAID
        # -------------------------------------------------

        if total_after_payment >= invoice_amount:

            connection.execute(
                """
                UPDATE invoices

                SET status = 'Paid'

                WHERE id = ?
                """,
                (
                    invoice["id"],
                )
            )

        # -------------------------------------------------
        # AUDIT LOG
        # -------------------------------------------------

        connection.execute(
            """
            INSERT INTO audit_logs
            (
                user_id,
                action,
                timestamp
            )

            VALUES (?, ?, datetime('now'))
            """,
            (
                session["user_id"],
                audit_action
            )
        )

    # =====================================================
    # REJECT PAYMENT
    # =====================================================

    else:

        new_status = "Rejected"

        audit_action = (
            "Rejected payment "
            + str(payment_id)
            + " for invoice "
            + str(invoice["invoice_number"])
        )

        connection.execute(
            """
            UPDATE payments

            SET status = ?

            WHERE id = ?
            """,
            (
                new_status,
                payment_id
            )
        )

        connection.execute(
            """
            INSERT INTO audit_logs
            (
                user_id,
                action,
                timestamp
            )

            VALUES (?, ?, datetime('now'))
            """,
            (
                session["user_id"],
                audit_action
            )
        )

    connection.commit()

    connection.close()

    # Re-check the invoice for fraud
    create_fraud_alerts(
        payment["invoice_id"]
    )

    return redirect(
        "/payment-approval"
    )


# =========================================================
# ADD PAYMENT
# =========================================================

@app.route(
    "/payments/add",
    methods=["GET", "POST"]
)
def add_payment():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    # =====================================================
    # ADD PAYMENT
    # =====================================================

    if request.method == "POST":

        invoice_id = request.form.get(
            "invoice_id",
            ""
        )

        amount = request.form.get(
            "amount",
            ""
        )

        payment_date = request.form.get(
            "payment_date",
            ""
        )

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if (
            not invoice_id
            or not amount
            or not payment_date
        ):

            connection.close()

            return "Please complete all payment fields."

        try:

            invoice_id = int(
                invoice_id
            )

        except ValueError:

            connection.close()

            return "Invalid invoice."

        try:

            amount = float(
                amount
            )

        except ValueError:

            connection.close()

            return "Payment amount must be a valid number."

        # -------------------------------------------------
        # PAYMENT AMOUNT MUST BE POSITIVE
        # -------------------------------------------------

        if amount <= 0:

            connection.close()

            return (
                "Payment amount must be greater than zero."
            )

        # -------------------------------------------------
        # FIND INVOICE
        # -------------------------------------------------

        invoice = connection.execute(
            """
            SELECT
                id,
                invoice_number,
                amount,
                status

            FROM invoices

            WHERE id = ?
            """,
            (invoice_id,)
        ).fetchone()

        if invoice is None:

            connection.close()

            return "Invoice not found."

        # -------------------------------------------------
        # ONLY VALID INVOICE STATUSES
        # -------------------------------------------------

        if invoice["status"] not in [
            "Pending",
            "Approved"
        ]:

            connection.close()

            return (
                "A payment can only be added to "
                "a Pending or Approved invoice."
            )

        invoice_amount = float(
            invoice["amount"] or 0
        )

        # -------------------------------------------------
        # EXISTING COMPLETED PAYMENTS
        # -------------------------------------------------

        completed_total = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)

            FROM payments

            WHERE invoice_id = ?

            AND status = 'Completed'
            """,
            (
                invoice_id,
            )
        ).fetchone()[0]

        completed_total = float(
            completed_total or 0
        )

        # -------------------------------------------------
        # EXISTING PENDING PAYMENTS
        # -------------------------------------------------

        pending_total = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)

            FROM payments

            WHERE invoice_id = ?

            AND status = 'Pending'
            """,
            (
                invoice_id,
            )
        ).fetchone()[0]

        pending_total = float(
            pending_total or 0
        )

        # -------------------------------------------------
        # PREVENT PAYMENT OVER INVOICE AMOUNT
        # -------------------------------------------------

        total_reserved = (
            completed_total
            + pending_total
        )

        if (
            total_reserved + amount
            > invoice_amount
        ):

            remaining = (
                invoice_amount
                - total_reserved
            )

            if remaining < 0:

                remaining = 0

            connection.close()

            return (
                f"Payment is too high. "
                f"The remaining available amount "
                f"for this invoice is "
                f"R{remaining:,.2f}."
            )

        # -------------------------------------------------
        # INSERT PAYMENT AS PENDING
        # -------------------------------------------------

        try:

            connection.execute(
                """
                INSERT INTO payments
                (
                    invoice_id,
                    amount,
                    payment_date,
                    status
                )

                VALUES
                (
                    ?,
                    ?,
                    ?,
                    'Pending'
                )
                """,
                (
                    invoice_id,
                    amount,
                    payment_date
                )
            )

            # -------------------------------------------------
            # AUDIT LOG
            # -------------------------------------------------

            connection.execute(
                """
                INSERT INTO audit_logs
                (
                    user_id,
                    action,
                    timestamp
                )

                VALUES (?, ?, datetime('now'))
                """,
                (
                    session["user_id"],
                    "Created payment for invoice "
                    + str(invoice["invoice_number"])
                )
            )

            connection.commit()

        except sqlite3.Error as error:

            connection.rollback()

            print(
                "Payment creation error:",
                error
            )

            connection.close()

            return (
                "An error occurred while creating "
                "the payment."
            )

        connection.close()

        # Re-check fraud
        create_fraud_alerts(
            invoice_id
        )

        return redirect(
            "/payment-tracking"
        )

    # =====================================================
    # GET INVOICES
    # =====================================================

    invoices = connection.execute(
        """
        SELECT
            invoices.id,
            invoices.invoice_number,
            invoices.amount,
            invoices.invoice_date,
            invoices.status,

            suppliers.name AS supplier_name

        FROM invoices

        LEFT JOIN suppliers
            ON invoices.supplier_id = suppliers.id

        WHERE invoices.status IN
        (
            'Pending',
            'Approved'
        )

        ORDER BY invoices.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "add_payment.html",

        invoices=invoices,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# REPORTS
# =========================================================

@app.route("/reports")
def reports():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_database()

    # =====================================================
    # INVOICE SUMMARY
    # =====================================================

    total_invoices = connection.execute(
        """
        SELECT COUNT(*)
        FROM invoices
        """
    ).fetchone()[0]

    total_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        """
    ).fetchone()[0]

    pending_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        WHERE status = 'Pending'
        """
    ).fetchone()[0]

    approved_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        WHERE status = 'Approved'
        """
    ).fetchone()[0]

    paid_invoice_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM invoices
        WHERE status = 'Paid'
        """
    ).fetchone()[0]

    # =====================================================
    # PAYMENT SUMMARY
    # =====================================================

    total_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        """
    ).fetchone()[0]

    completed_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    pending_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Pending'
        """
    ).fetchone()[0]

    rejected_payments = connection.execute(
        """
        SELECT COUNT(*)
        FROM payments
        WHERE status = 'Rejected'
        """
    ).fetchone()[0]

    total_payment_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        """
    ).fetchone()[0]

    completed_payment_value = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE status = 'Completed'
        """
    ).fetchone()[0]

    # =====================================================
    # SUPPLIER SUMMARY
    # =====================================================

    total_suppliers = connection.execute(
        """
        SELECT COUNT(*)
        FROM suppliers
        """
    ).fetchone()[0]

    # =====================================================
    # FRAUD SUMMARY
    # =====================================================

    total_fraud_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        """
    ).fetchone()[0]

    open_fraud_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE status = 'Open'
        """
    ).fetchone()[0]

    critical_fraud_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE severity = 'Critical'
        AND status = 'Open'
        """
    ).fetchone()[0]

    high_fraud_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE severity = 'High'
        AND status = 'Open'
        """
    ).fetchone()[0]

    medium_fraud_alerts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fraud_alerts
        WHERE severity = 'Medium'
        AND status = 'Open'
        """
    ).fetchone()[0]

    # =====================================================
    # INVOICE STATUS BREAKDOWN
    # =====================================================

    invoice_status = connection.execute(
        """
        SELECT
            status,
            COUNT(*) AS count,
            COALESCE(SUM(amount), 0) AS value

        FROM invoices

        GROUP BY status

        ORDER BY count DESC
        """
    ).fetchall()

    # =====================================================
    # SUPPLIER SPENDING
    # =====================================================

    supplier_spending = connection.execute(
        """
        SELECT
            suppliers.name AS supplier_name,

            COUNT(invoices.id) AS invoice_count,

            COALESCE(
                SUM(invoices.amount),
                0
            ) AS total_value

        FROM suppliers

        LEFT JOIN invoices
            ON suppliers.id =
               invoices.supplier_id

        GROUP BY
            suppliers.id,
            suppliers.name

        ORDER BY total_value DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "reports.html",

        total_invoices=
            total_invoices,

        total_invoice_value=
            float(
                total_invoice_value or 0
            ),

        pending_invoice_value=
            float(
                pending_invoice_value or 0
            ),

        approved_invoice_value=
            float(
                approved_invoice_value or 0
            ),

        paid_invoice_value=
            float(
                paid_invoice_value or 0
            ),

        total_payments=
            total_payments,

        completed_payments=
            completed_payments,

        pending_payments=
            pending_payments,

        rejected_payments=
            rejected_payments,

        total_payment_value=
            float(
                total_payment_value or 0
            ),

        completed_payment_value=
            float(
                completed_payment_value or 0
            ),

        total_suppliers=
            total_suppliers,

        total_fraud_alerts=
            total_fraud_alerts,

        open_fraud_alerts=
            open_fraud_alerts,

        critical_fraud_alerts=
            critical_fraud_alerts,

        high_fraud_alerts=
            high_fraud_alerts,

        medium_fraud_alerts=
            medium_fraud_alerts,

        invoice_status=
            invoice_status,

        supplier_spending=
            supplier_spending,

        username=session.get(
            "username",
            ""
        ),

        role=session.get(
            "role",
            ""
        )
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )

