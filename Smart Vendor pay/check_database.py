import sqlite3

DATABASE = "smart_vendor_pay.db"

connection = sqlite3.connect(DATABASE)

# Get all tables
tables = connection.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

print("\n======================================")
print("SMART VENDOR PAY DATABASE")
print("======================================")

print("\nTables found:")

for table in tables:
    print("-", table[0])

print("\n======================================")
print("TABLE STRUCTURES")
print("======================================")

for table in tables:

    table_name = table[0]

    print(f"\n[{table_name}]")

    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    for column in columns:

        column_id = column[0]
        column_name = column[1]
        data_type = column[2]
        not_null = column[3]
        default_value = column[4]
        primary_key = column[5]

        print(
            f"  {column_name} | "
            f"{data_type} | "
            f"Primary Key: {primary_key} | "
            f"Not Null: {not_null}"
        )

connection.close()

print("\n======================================")
print("DATABASE CHECK COMPLETE")
print("======================================")
