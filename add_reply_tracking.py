"""
Migration script to add reply tracking columns and table.
Run this script once to update the database schema.
"""
import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('leads.db')
c = conn.cursor()

print("🔄 Adding reply tracking columns to leads table...")

# Add new columns to leads table (SQLite doesn't support IF NOT EXISTS for columns)
try:
    c.execute('ALTER TABLE leads ADD COLUMN my_comment_id TEXT')
    print("  ✅ Added my_comment_id column")
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e).lower():
        print("  ℹ️ my_comment_id column already exists")
    else:
        raise

try:
    c.execute('ALTER TABLE leads ADD COLUMN reply_count INTEGER DEFAULT 0')
    print("  ✅ Added reply_count column")
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e).lower():
        print("  ℹ️ reply_count column already exists")
    else:
        raise

try:
    c.execute('ALTER TABLE leads ADD COLUMN last_checked_at TEXT')
    print("  ✅ Added last_checked_at column")
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e).lower():
        print("  ℹ️ last_checked_at column already exists")
    else:
        raise

print("\n🔄 Creating replies table...")

c.execute('''
CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id TEXT NOT NULL,
    reply_id TEXT UNIQUE NOT NULL,
    author TEXT,
    body TEXT,
    score INTEGER DEFAULT 0,
    created_utc REAL,
    is_read INTEGER DEFAULT 0,
    found_at TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
)
''')
print("  ✅ Created replies table")

# Create index for faster lookups
c.execute('CREATE INDEX IF NOT EXISTS idx_replies_lead_id ON replies(lead_id)')
c.execute('CREATE INDEX IF NOT EXISTS idx_replies_is_read ON replies(is_read)')
print("  ✅ Created indexes")

conn.commit()
conn.close()

print("\n🎉 Reply tracking migration complete!")
