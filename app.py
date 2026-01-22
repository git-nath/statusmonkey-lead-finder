from flask import Flask, render_template, jsonify, request
import requests
import time
import json
import sqlite3
from datetime import datetime
import os
from notion_client import Client

app = Flask(__name__)

# Notion API Configuration
NOTION_API_KEY = "ntn_f92115249684DSCjMeZGcN7j7JU6tPkWrNRskbOj9AQ6zP"
NOTION_DATABASE_ID = "2f02250cb76880859face42b2ae7fe33"
notion = Client(auth=NOTION_API_KEY)

# ============================================
# DATABASE HELPER FUNCTIONS
# ============================================

def get_db_connection():
    """Create database connection with Row factory for dict-like access"""
    conn = sqlite3.connect('leads.db')
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """Convert sqlite3.Row to dictionary"""
    return dict(zip(row.keys(), row))

# ============================================
# KEYWORDS & SCORING (Unchanged)
# ============================================

KEYWORDS = {
    'urgent_leads': [
        'my website is down', 'site went down', 'server is down',
        'experiencing downtime', 'users cant access', 'website not responding',
        'how do I know if my site is down', 'monitor website uptime',
        'site is down', 'website down', 'cant access my site'
    ],
    'competitor_complaints': [
        'pingdom too expensive', 'uptimerobot alternatives', 
        'statuspage pricing', 'better uptime cost',
        'monitoring tool recommendations', 'cheap uptime monitoring',
        'pingdom alternative', 'uptimerobot too expensive'
    ],
    'buying_signals': [
        'need uptime monitoring', 'looking for monitoring tool',
        'which monitoring service', 'best uptime checker',
        'website monitoring service', 'downtime alerts',
        'recommend monitoring tool', 'uptime monitoring recommendations'
    ],
    'perfect_customers': [
        'startup', 'small business', 'side project', 'personal website',
        'just launched', 'new website', 'saas founder', 'indie hacker',
        'solopreneur', 'bootstrap'
    ],
    'competitors': [
        'pingdom', 'uptimerobot', 'statuspage', 'better uptime',
        'freshping', 'statuscake', 'site24x7', 'uptime robot'
    ]
}

def score_lead(post):
    """Enhanced lead scoring for StatusMonkey"""
    text = (post['title'] + ' ' + post.get('text', '')).lower()
    score = 0
    matched_keywords = []
    priority = 'cold'
    suggested_template = 'recommendation'
    
    # EMERGENCY: Site is DOWN right now!
    for keyword in KEYWORDS['urgent_leads']:
        if keyword in text:
            score += 50
            matched_keywords.append(f"🚨urgent:{keyword}")
            priority = 'emergency'
            suggested_template = 'downtime_issue'
    
    # Competitor complaints
    for keyword in KEYWORDS['competitor_complaints']:
        if keyword in text:
            score += 30
            matched_keywords.append(f"💰competitor_complaint:{keyword}")
            if priority != 'emergency':
                priority = 'hot'
            suggested_template = 'competitor_complaint'
    
    # Buying signals
    for keyword in KEYWORDS['buying_signals']:
        if keyword in text:
            score += 20
            matched_keywords.append(f"🎯buying_signal:{keyword}")
    
    # Perfect customer profile
    for keyword in KEYWORDS['perfect_customers']:
        if keyword in text:
            score += 15
            matched_keywords.append(f"✨ideal_customer:{keyword}")
    
    # Competitor mentions
    for competitor in KEYWORDS['competitors']:
        if competitor in text:
            score += 10
            matched_keywords.append(f"👀competitor:{competitor}")
    
    # Budget keywords
    budget_keywords = ['cheap', 'affordable', 'budget', 'free', 'expensive']
    for keyword in budget_keywords:
        if keyword in text:
            score += 10
            matched_keywords.append(f"💵budget:{keyword}")
    
    # Determine priority based on score
    if score >= 50:
        priority = 'emergency'
    elif score >= 30:
        priority = 'hot'
    elif score >= 15:
        priority = 'warm'
    else:
        priority = 'cold'
    
    return {
        'score': score,
        'priority': priority,
        'matched_keywords': matched_keywords,
        'suggested_template': suggested_template
    }

# ============================================
# REDDIT SCRAPING FUNCTIONS
# ============================================

def fetch_reddit_posts(subreddit, limit=50):
    """Fetch posts from a subreddit"""
    url = f'https://www.reddit.com/r/{subreddit}/new/.json?limit={limit}'
    headers = {'User-Agent': 'StatusMonkeyFinder/1.9'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        posts = []
        for item in data['data']['children']:
            post = item['data']
            post_url = f"https://www.reddit.com{post['permalink']}"
            
            posts.append({
                'id': post['id'],
                'title': post['title'],
                'author': post['author'],
                'subreddit': post['subreddit'],
                'score': post['score'],
                'comments': post['num_comments'],
                'url': post_url,
                'text': post.get('selftext', '')[:500],
                'created': post['created_utc'],
                'created_readable': datetime.fromtimestamp(post['created_utc']).strftime('%Y-%m-%d %H:%M')
            })
        
        return posts
    except Exception as e:
        print(f"Error fetching from r/{subreddit}: {e}")
        return []

def scan_reddit():
    """Scan Reddit for new leads"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get active subreddits from database
    c.execute('SELECT name FROM subreddits WHERE active = 1')
    subreddits = [row['name'] for row in c.fetchall()]
    
    if not subreddits:
        conn.close()
        print("⚠️ No subreddits configured!")
        return 0
    
    # Get existing lead IDs
    c.execute('SELECT id FROM leads')
    existing_ids = {row['id'] for row in c.fetchall()}
    
    new_leads = 0
    
    for subreddit in subreddits:
        print(f"Scanning r/{subreddit}...")
        posts = fetch_reddit_posts(subreddit, limit=50)
        
        for post in posts:
            # Skip if already processed
            if post['id'] in existing_ids:
                continue
            
            # Check if post matches any keywords
            lead_info = score_lead(post)
            
            if lead_info['score'] > 0:
                # Insert lead into database
                c.execute('''
                    INSERT INTO leads (
                        id, title, author, subreddit, score, comments, url, text,
                        created, created_readable, priority, matched_keywords,
                        suggested_template, lead_score, status, found_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post['id'],
                    post['title'],
                    post['author'],
                    post['subreddit'],
                    post['score'],
                    post['comments'],
                    post['url'],
                    post['text'],
                    post['created'],
                    post['created_readable'],
                    lead_info['priority'],
                    json.dumps(lead_info['matched_keywords']),
                    lead_info['suggested_template'],
                    lead_info['score'],
                    'new',
                    datetime.now().isoformat()
                ))
                new_leads += 1
        
        time.sleep(2)  # Rate limiting
    
    conn.commit()
    conn.close()
    return new_leads

# ============================================
# FLASK ROUTES
# ============================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/leads')
def get_leads():
    """Get all leads"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM leads ORDER BY created DESC')
    leads = [dict_from_row(row) for row in c.fetchall()]
    conn.close()
    
    # Parse matched_keywords JSON string back to list
    for lead in leads:
        if lead['matched_keywords']:
            try:
                lead['matched_keywords'] = json.loads(lead['matched_keywords'])
            except:
                lead['matched_keywords'] = []
        else:
            lead['matched_keywords'] = []
    
    return jsonify(leads)

@app.route('/api/scan', methods=['POST'])
def scan():
    """Trigger new scan"""
    new_count = scan_reddit()
    return jsonify({'success': True, 'new_leads': new_count})

@app.route('/api/lead/<lead_id>', methods=['PUT', 'DELETE'])
def update_or_delete_lead(lead_id):
    """Update lead status or notes OR delete lead"""
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'DELETE':
        try:
            c.execute('DELETE FROM leads WHERE id = ?', (lead_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Lead deleted'})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500

    # PUT logic for update
    update = request.json
    
    if 'status' in update:
        c.execute('UPDATE leads SET status = ?, status_updated_at = ? WHERE id = ?',
                 (update['status'], datetime.now().isoformat(), lead_id))
        if update['status'] == 'contacted':
            c.execute('UPDATE leads SET replied_at = ? WHERE id = ?',
                     (datetime.now().isoformat(), lead_id))
    
    if 'notes' in update:
        c.execute('UPDATE leads SET notes = ? WHERE id = ?',
                 (update['notes'], lead_id))
    
    if 'converted' in update:
        converted = 1 if update['converted'] else 0
        revenue = 5.99 if update['converted'] else 0
        c.execute('UPDATE leads SET converted = ?, revenue = ? WHERE id = ?',
                 (converted, revenue, lead_id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/stats')
def get_stats():
    """Get analytics stats"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Total leads
    c.execute('SELECT COUNT(*) as total FROM leads')
    total = c.fetchone()['total']
    
    # Priority counts
    c.execute('SELECT COUNT(*) as count FROM leads WHERE priority = ?', ('emergency',))
    emergency = c.fetchone()['count']
    
    c.execute('SELECT COUNT(*) as count FROM leads WHERE priority = ?', ('hot',))
    hot = c.fetchone()['count']
    
    c.execute('SELECT COUNT(*) as count FROM leads WHERE priority = ?', ('warm',))
    warm = c.fetchone()['count']
    
    c.execute('SELECT COUNT(*) as count FROM leads WHERE priority = ?', ('cold',))
    cold = c.fetchone()['count']
    
    # Status counts
    c.execute('SELECT COUNT(*) as count FROM leads WHERE status = ?', ('contacted',))
    contacted = c.fetchone()['count']
    
    c.execute('SELECT COUNT(*) as count FROM leads WHERE converted = 1')
    converted = c.fetchone()['count']
    
    # Revenue
    c.execute('SELECT SUM(revenue) as total FROM leads')
    revenue = c.fetchone()['total'] or 0
    
    # Conversion rate
    conversion_rate = (converted / contacted * 100) if contacted > 0 else 0
    
    # Top subreddits
    c.execute('''
        SELECT subreddit, COUNT(*) as count 
        FROM leads 
        GROUP BY subreddit 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    top_subreddits = [(row['subreddit'], row['count']) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'total': total,
        'emergency': emergency,
        'hot': hot,
        'warm': warm,
        'cold': cold,
        'contacted': contacted,
        'converted': converted,
        'revenue': round(revenue, 2),
        'conversion_rate': round(conversion_rate, 1),
        'top_subreddits': top_subreddits
    })

@app.route('/api/templates')
def get_templates():
    """Get reply templates"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT name, content FROM templates')
    templates = {row['name']: row['content'] for row in c.fetchall()}
    conn.close()
    return jsonify(templates)

@app.route('/api/keywords')
def get_keywords():
    """Get current keywords"""
    return jsonify(KEYWORDS)

# ============================================
# REDDIT FULL POST FETCHER - v2.0
# ============================================

@app.route('/api/reddit/full/<post_id>')
def get_full_reddit_post(post_id):
    """Fetch full Reddit post with all comments"""
    try:
        # Find lead in database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM leads WHERE id = ?', (post_id,))
        lead = c.fetchone()
        conn.close()
        
        if not lead:
            return jsonify({'success': False, 'error': 'Lead not found'}), 404
        
        # Extract Reddit post ID from URL
        # URL format: https://www.reddit.com/r/subreddit/comments/POST_ID/title/
        reddit_id = lead['id']
        subreddit = lead['subreddit']
        
        # Fetch from Reddit API
        url = f'https://www.reddit.com/r/{subreddit}/comments/{reddit_id}.json'
        headers = {'User-Agent': 'StatusMonkeyFinder/2.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # Parse post
        post_data = data[0]['data']['children'][0]['data']
        
        # Parse comments
        comments = []
        if len(data) > 1:
            comments = parse_comments(data[1]['data']['children'])
        
        result = {
            'success': True,
            'title': post_data['title'],
            'author': post_data['author'],
            'selftext': post_data.get('selftext', ''),
            'url': f"https://www.reddit.com{post_data['permalink']}",
            'score': post_data['score'],
            'num_comments': post_data['num_comments'],
            'comments': comments
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error fetching full post: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def parse_comments(comment_list, depth=0):
    """Recursively parse Reddit comments"""
    comments = []
    
    for item in comment_list:
        if item['kind'] == 't1':  # Comment
            comment = item['data']
            
            comment_obj = {
                'author': comment.get('author', '[deleted]'),
                'body': comment.get('body', '[removed]'),
                'score': comment.get('score', 0),
                'depth': depth
            }
            
            comments.append(comment_obj)
            
            # Parse replies
            if 'replies' in comment and comment['replies']:
                if isinstance(comment['replies'], dict):
                    replies = parse_comments(
                        comment['replies']['data']['children'],
                        depth + 1
                    )
                    comments.extend(replies)
    
    return comments

# ============================================
# SUBREDDIT MANAGEMENT - v2.3
# ============================================

@app.route('/api/subreddits', methods=['GET'])
def get_subreddits():
    """Get all tracked subreddits"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT name, priority, added_date FROM subreddits WHERE active = 1 ORDER BY name')
    subreddits = [dict_from_row(row) for row in c.fetchall()]
    conn.close()
    return jsonify(subreddits)

@app.route('/api/subreddits', methods=['POST'])
def add_subreddit():
    """Add a new subreddit to track"""
    data = request.json
    subreddit_name = data.get('name', '').strip()
    priority = data.get('priority', 'medium_priority')
    
    if not subreddit_name:
        return jsonify({'success': False, 'error': 'Subreddit name required'}), 400
    
    # Remove r/ prefix if included
    if subreddit_name.startswith('r/'):
        subreddit_name = subreddit_name[2:]
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('INSERT INTO subreddits (name, priority) VALUES (?, ?)', 
                 (subreddit_name, priority))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Added r/{subreddit_name}'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'error': 'Subreddit already exists'}), 400

@app.route('/api/subreddits/<name>', methods=['DELETE'])
def delete_subreddit(name):
    """Remove a subreddit from tracking"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE subreddits SET active = 0 WHERE name = ?', (name,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Removed r/{name}'})

# ============================================
# STATUS UPDATE ENDPOINT
# ============================================

@app.route('/update_status', methods=['POST'])
def update_status():
    """Update lead status (used by frontend)"""
    try:
        data = request.json
        lead_id = data.get('lead_id')
        new_status = data.get('status')
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE leads SET status = ?, status_updated_at = ? WHERE id = ?',
                 (new_status, datetime.now().isoformat(), lead_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# NOTION INTEGRATION
# ============================================

@app.route('/api/notion/add', methods=['POST'])
def add_to_notion():
    """Send a lead to Notion database"""
    try:
        data = request.json
        lead_id = data.get('lead_id')
        
        if not lead_id:
            return jsonify({'success': False, 'error': 'Lead ID required'}), 400
        
        # Get lead from database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
        lead = c.fetchone()
        conn.close()
        
        if not lead:
            return jsonify({'success': False, 'error': 'Lead not found'}), 404
        
        # Create page in Notion database
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Post Title": {
                    "title": [
                        {
                            "text": {
                                "content": lead['title'][:2000]  # Notion has a 2000 char limit for titles
                            }
                        }
                    ]
                },
                "URL": {
                    "url": lead['url']
                },
                "Status": {
                    "select": {
                        "name": "Contacted"
                    }
                }
            }
        )
        
        return jsonify({'success': True, 'message': 'Lead added to Notion successfully'})
        
    except Exception as e:
        print(f"Error adding to Notion: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# START SERVER
# ============================================

if __name__ == '__main__':
    print("🚀 StatusMonkey Lead Finder v2.3 Starting...")
    print("📊 Dashboard: http://localhost:5000")
    print("✨ NEW: SQLite database + Subreddit management!")
    app.run(debug=True, port=5000)
