CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    subreddit TEXT,
    score INTEGER,
    comments INTEGER,
    url TEXT,
    text TEXT,
    created DOUBLE PRECISION,
    created_readable TEXT,
    priority TEXT,
    matched_keywords TEXT,
    suggested_template TEXT,
    lead_score INTEGER,
    status TEXT DEFAULT 'new',
    notes TEXT,
    replied_at TEXT,
    converted INTEGER DEFAULT 0,
    revenue DOUBLE PRECISION DEFAULT 0,
    found_at TEXT,
    status_updated_at TEXT,
    sent_to_notion INTEGER DEFAULT 0,
    notion_thread_number INTEGER,
    comment_url TEXT,
    comment_snippet TEXT
);

CREATE TABLE IF NOT EXISTS subreddits (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    added_date TEXT DEFAULT CURRENT_TIMESTAMP,
    active INTEGER DEFAULT 1,
    priority TEXT DEFAULT 'medium_priority'
);

CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL
);
