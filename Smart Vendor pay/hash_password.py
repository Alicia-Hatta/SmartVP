from werkzeug.security import generate_password_hash
import sqlite3

connection = sqlite3.connect("smart_vendor_pay.db")

hashed_password = generate_password_hash("admin123")

connection.execute(
    """
    UPDATE users
    SET password = ?
    WHERE username = ?
    """,
    (hashed_password, "admin")
)

connection.commit()
connection.close()

print("Admin password successfully hashed.")