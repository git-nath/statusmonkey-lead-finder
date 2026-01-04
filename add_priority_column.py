import sqlite3

conn = sqlite3.connect('leads.db')
c = conn.cursor()

# Add priority column to subreddits table
try:
    c.execute('ALTER TABLE subreddits ADD COLUMN priority TEXT DEFAULT "medium_priority"')
    print("✅ Added priority column!")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("ℹ️ Priority column already exists")
    else:
        print(f"❌ Error: {e}")

# Update existing subreddits with default priorities
high_priority_subs = ['webdev', 'SaaS', 'startups', 'Entrepreneur']

for sub in high_priority_subs:
    c.execute('UPDATE subreddits SET priority = ? WHERE name = ?', ('high_priority', sub))

c.execute('UPDATE subreddits SET priority = "medium_priority" WHERE priority IS NULL OR priority = ""')

conn.commit()
conn.close()

print("✅ Database schema updated!")
