import sqlite3

DATABASE = "smart_vendor_pay.db"


def create_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Suppliers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            bank_name TEXT,
            account_number TEXT,
            risk_score REAL DEFAULT 0
        )
    """)

    # Invoices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            invoice_number TEXT NOT NULL,
            amount REAL NOT NULL,
            invoice_date TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    """)

    # Payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
    """)

    # Fraud alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fraud_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            severity TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
    """)

    # Audit logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()

    print("Database created successfully!")


def add_test_user():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role)
        VALUES (?, ?, ?)
    """, ("admin", "admin123", "Finance Manager"))

    connection.commit()
    connection.close()

    print("Test user created!")


if __name__ == "__main__":
    create_database()
    add_test_user()