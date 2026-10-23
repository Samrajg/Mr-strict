import sqlite3

conn = sqlite3.connect('app.db')
cur = conn.cursor()

columns = [row[1] for row in cur.execute("PRAGMA table_info(assignment)").fetchall()]
if 'workspace_name' not in columns:
    cur.execute("ALTER TABLE assignment ADD COLUMN workspace_name VARCHAR(100) DEFAULT 'default'")
    print("Column workspace_name added successfully.")
else:
    print("Column workspace_name already exists.")

conn.commit()
conn.close()
