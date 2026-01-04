import sqlite3
import json
import os

# Connect to database
conn = sqlite3.connect('leads.db')
c = conn.cursor()

# Create leads table
c.execute('''
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    subreddit TEXT,
    score INTEGER,
    comments INTEGER,
    url TEXT,
    text TEXT,
    created REAL,
    created_readable TEXT,
    priority TEXT,
    matched_keywords TEXT,
    suggested_template TEXT,
    lead_score INTEGER,
    status TEXT DEFAULT 'new',
    notes TEXT,
    replied_at TEXT,
    converted INTEGER DEFAULT 0,
    revenue REAL DEFAULT 0,
    found_at TEXT,
    status_updated_at TEXT
)
''')

# Create templates table
c.execute('''
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL
)
''')

conn.commit()
print("✅ Database tables created!")

# Insert default templates
templates = [
    ('downtime_issue', 'Hey! I use StatusMonkey.co for this - it checks every 60 seconds and sends SMS alerts instantly. Only $5.99/mo (free during beta). Has saved me multiple times!'),
    ('competitor_complaint', 'If you think [COMPETITOR] is expensive, check out StatusMonkey. $5.99/mo with 60-second checks, SMS alerts, AND a status page included. Currently free during beta.'),
    ('recommendation', 'I have been using StatusMonkey and it is solid. 60-second monitoring, instant SMS/email alerts, and you get a status page. Best part? Only $5.99/mo and free during beta.')
]

for name, content in templates:
    try:
        c.execute('INSERT INTO templates (name, content) VALUES (?, ?)', (name, content))
    except:
        pass

conn.commit()
print("✅ Default templates added!")

# Migrate existing JSON data if exists
if os.path.exists('data/leads.json'):
    print("\n📦 Migrating existing leads from JSON...")
    with open('data/leads.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    leads = data.get('leads', [])
    migrated = 0
    
    for lead in leads:
        try:
            c.execute('''
                INSERT OR IGNORE INTO leads (
                    id, title, author, subreddit, score, comments, url, text,
                    created, created_readable, priority, matched_keywords, 
                    suggested_template, lead_score, status, notes, replied_at,
                    converted, revenue, found_at, status_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead.get('id'),
                lead.get('title'),
                lead.get('author'),
                lead.get('subreddit'),
                lead.get('score'),
                lead.get('comments'),
                lead.get('url'),
                lead.get('text'),
                lead.get('created'),
                lead.get('created_readable'),
                lead.get('priority'),
                json.dumps(lead.get('matched_keywords', [])),
                lead.get('suggested_template'),
                lead.get('score'),
                lead.get('status', 'new'),
                lead.get('notes', ''),
                lead.get('replied_at'),
                1 if lead.get('converted') else 0,
                lead.get('revenue', 0),
                lead.get('found_at'),
                lead.get('status_updated_at')
            ))
            migrated += 1
        except Exception as e:
            print(f"⚠️ Error migrating lead {lead.get('id')}: {e}")
    
    conn.commit()
    print(f"✅ Migrated {migrated} leads from JSON!")
else:
    print("ℹ️ No existing JSON data found")

conn.close()
print("\n🎉 Migration complete! Database ready!")
