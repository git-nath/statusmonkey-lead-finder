import sqlite3

conn = sqlite3.connect('leads.db')
c = conn.cursor()

# Get all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()

print("📊 EXISTING TABLES:")
print("=" * 40)
for table in tables:
    print(f"✅ {table[0]}")
    
print("\n" + "=" * 40)

# Check each table's structure and data
for table in tables:
    table_name = table[0]
    print(f"\n📋 TABLE: {table_name}")
    print("-" * 40)
    
    # Get column info
    c.execute(f"PRAGMA table_info({table_name})")
    columns = c.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Count rows
    c.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = c.fetchone()[0]
    print(f"Rows: {count}")
    
    # Show sample data if exists
    if count > 0:
        c.execute(f"SELECT * FROM {table_name} LIMIT 3")
        rows = c.fetchall()
        print(f"Sample data:")
        for row in rows:
            print(f"  {row}")

conn.close()
print("\n✅ Database check complete!")
