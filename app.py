from flask import Flask, render_template, jsonify, request
import requests
import time
import json
from datetime import datetime
import os
from notion_client import Client

from db import (
    DBIntegrityError,
    close_db_connection,
    dict_from_row,
    get_db_connection,
    initialize_database,
)

app = Flask(__name__)

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_BACKGROUND_TOPICS = [
    "nature",
    "minimal",
    "mountains",
    "sunrise",
    "landscape",
    "calm",
]


@app.teardown_appcontext
def close_connection(exception=None):
    close_db_connection(exception)


@app.teardown_request
def close_connection_after_request(exception=None):
    close_db_connection(exception)

# Notion API Configuration
NOTION_API_KEY = "ntn_f92115249684DSCjMeZGcN7j7JU6tPkWrNRskbOj9AQ6zP"
NOTION_DATABASE_ID = "2f02250cb76880859face42b2ae7fe33"
notion = Client(auth=NOTION_API_KEY)

# ============================================
# DATABASE HELPER FUNCTIONS
# ============================================
# All reads/writes now go to Supabase Postgres via DATABASE_URL.
# SQLite is no longer used at runtime.

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

    try:
        # Get active subreddits from database
        c.execute('SELECT name FROM subreddits WHERE active = 1')
        subreddits = [row['name'] for row in c.fetchall()]

        if not subreddits:
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
                        ON CONFLICT (id) DO NOTHING
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
        return new_leads
    finally:
        conn.close()

# ============================================
# FLASK ROUTES
# ============================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    """Admin dashboard"""
    return render_template('admin.html')


@app.route('/api/background-image')
def get_background_image():
    """Return a curated Unsplash image for dashboard wallpaper."""
    if not UNSPLASH_ACCESS_KEY:
        return jsonify({
            'error': 'Unsplash API key is not configured. Set UNSPLASH_ACCESS_KEY.'
        }), 503

    endpoint = 'https://api.unsplash.com/photos/random'
    params = {
        'query': ','.join(UNSPLASH_BACKGROUND_TOPICS),
        'orientation': 'landscape',
        'content_filter': 'high',
        'count': 1,
    }
    headers = {
        'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}'
    }

    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json()
        photo = payload[0] if isinstance(payload, list) else payload

        photographer_name = photo.get('user', {}).get('name', 'Unknown photographer')
        photographer_link = photo.get('user', {}).get('links', {}).get('html', 'https://unsplash.com')
        unsplash_link = (photo.get('links', {}) or {}).get('html', 'https://unsplash.com')

        urls = photo.get('urls', {}) or {}

        return jsonify({
            'image_url': urls.get('raw') or urls.get('full') or urls.get('regular'),
            'image_url_full': urls.get('full') or urls.get('regular'),
            'image_url_small': urls.get('regular') or urls.get('small'),
            'alt_description': photo.get('alt_description') or 'Scenic workspace wallpaper',
            'photographer_name': photographer_name,
            'photographer_link': f"{photographer_link}?utm_source=statusmonkey&utm_medium=referral",
            'unsplash_link': f"{unsplash_link}?utm_source=statusmonkey&utm_medium=referral",
            'fetched_at': datetime.utcnow().isoformat(),
        })
    except requests.RequestException as exc:
        return jsonify({'error': f'Failed to fetch Unsplash image: {exc}'}), 502

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
# ADMIN API ENDPOINTS
# ============================================

@app.route('/api/admin/stats')
def get_admin_stats():
    """Get detailed system and database stats"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Database size
    db_size = os.path.getsize('leads.db') if os.path.exists('leads.db') else 0
    
    # Notion Sync Rate
    c.execute("SELECT COUNT(*) as total FROM leads WHERE status = 'contacted'")
    total_contacted = c.fetchone()['total']
    
    c.execute('SELECT COUNT(*) as sent FROM leads WHERE sent_to_notion = 1')
    total_sent = c.fetchone()['sent']
    
    sync_rate = (total_sent / total_contacted * 100) if total_contacted > 0 else 0
    
    # Subreddits (active vs inactive)
    c.execute('SELECT COUNT(*) as count FROM subreddits WHERE active = 1')
    active_subs = c.fetchone()['count']
    
    c.execute('SELECT COUNT(*) as count FROM subreddits WHERE active = 0')
    inactive_subs = c.fetchone()['count']
    
    # New leads in last 24h
    c.execute(
        "SELECT COUNT(*) as count FROM leads "
        "WHERE found_at::timestamp >= NOW() - INTERVAL '1 day'"
    )
    new_24h = c.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'db_size_kb': round(db_size / 1024, 2),
        'notion_sync_rate': round(sync_rate, 1),
        'active_subreddits': active_subs,
        'inactive_subreddits': inactive_subs,
        'leads_last_24h': new_24h,
        'python_version': '3.x',  # Static for now
        'db_health': 'Healthy' if os.path.exists('leads.db') else 'Error'
    })

@app.route('/api/admin/keywords')
def get_admin_keywords():
    """Return categorized keywords and scoring rules for inspection"""
    return jsonify({
        'categories': KEYWORDS,
        'base_scoring': {
            'urgent': 50,
            'competitor_complaint': 30,
            'buying_signal': 20,
            'ideal_customer': 15,
            'competitor_mention': 10,
            'budget_mention': 10
        }
    })

@app.route('/api/admin/databases')
def get_admin_databases():
    """List tracked database files in the project root"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_files = []

    for filename in os.listdir(base_dir):
        if not filename.endswith('.db'):
            continue
        path = os.path.join(base_dir, filename)
        if not os.path.isfile(path):
            continue
        size_kb = round(os.path.getsize(path) / 1024, 2)
        modified_at = datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
        db_files.append({
            'name': filename,
            'size_kb': size_kb,
            'modified_at': modified_at
        })

    db_files.sort(key=lambda entry: entry['name'])

    return jsonify({'databases': db_files})

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
    except DBIntegrityError:
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

def get_next_thread_number():
    """Get the next thread number by querying Notion database for the current max"""
    try:
        # Query Notion database to find the highest thread number
        results = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            sorts=[{
                "property": "Thread Number",
                "direction": "descending"
            }],
            page_size=1
        )
        
        if results['results']:
            # Get the first (highest) thread number
            first_page = results['results'][0]
            thread_prop = first_page['properties'].get('Thread Number', {})
            
            # Handle number property type
            if 'number' in thread_prop and thread_prop['number'] is not None:
                return int(thread_prop['number']) + 1
        
        # If no entries or couldn't parse, start from 1
        return 1
    except Exception as e:
        print(f"Error getting next thread number: {e}")
        return 1

def init_db():
    """Initialize the database and ensure all tables and columns exist"""
    initialize_database()

def should_initialize_database_on_startup():
    """Avoid expensive startup migrations in the reloader parent process."""
    if not app.debug:
        return True
    return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'


if should_initialize_database_on_startup():
    init_db()

@app.route('/api/notion/add', methods=['POST'])
def add_to_notion():
    """Send a single lead to Notion database"""
    try:
        data = request.json
        lead_id = data.get('lead_id')
        thread_number = data.get('thread_number')  # Get thread number from frontend
        
        if not lead_id:
            return jsonify({'success': False, 'error': 'Lead ID required'}), 400
        
        if not thread_number:
            return jsonify({'success': False, 'error': 'Thread number required'}), 400

        # Get lead from database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
        lead = c.fetchone()
        
        if not lead:
            conn.close()
            return jsonify({'success': False, 'error': 'Lead not found'}), 404
        
        # Check if already sent to Notion
        if lead['sent_to_notion'] == 1:
            conn.close()
            return jsonify({
                'success': False, 
                'error': 'Already sent to Notion', 
                'already_sent': True,
                'thread_number': lead['notion_thread_number']
            }), 400
        
        # Create page in Notion database with the provided thread number

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Post Title": {
                    "title": [
                        {
                            "text": {
                                "content": lead['title'][:2000]  # Notion has a 2000 char limit

                            }
                        }
                    ]
                },
                "URL": {
                    "url": lead['url']
                },
                "Thread Number": {
                    "number": int(thread_number)
                },

                "Status": {
                    "select": {
                        "name": "Contacted"
                    }
                }
            }
        )
        
        # Mark as sent to Notion and save thread number
        c.execute('UPDATE leads SET sent_to_notion = 1, notion_thread_number = ? WHERE id = ?', 
                 (thread_number, lead_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Lead added to Notion as #{thread_number}',
            'thread_number': thread_number
        })

        
    except Exception as e:
        print(f"Error adding to Notion: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notion/add-all', methods=['POST'])
def add_all_to_notion():
    """Send all unsent contacted leads to Notion database"""
    try:
        # Get all contacted leads that haven't been sent to Notion
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM leads 
            WHERE status = 'contacted' 
            AND (sent_to_notion IS NULL OR sent_to_notion = 0)
        ''')
        leads = c.fetchall()
        
        if not leads:
            conn.close()
            return jsonify({'success': True, 'message': 'No unsent leads to add', 'count': 0})
        
        # Get starting thread number
        next_thread_number = get_next_thread_number()

        success_count = 0
        error_count = 0
        errors = []
        
        for lead in leads:
            try:
                # Create page in Notion database
                notion.pages.create(
                    parent={"database_id": NOTION_DATABASE_ID},
                    properties={
                        "Post Title": {
                            "title": [
                                {
                                    "text": {
                                        "content": lead['title'][:2000]
                                    }
                                }
                            ]
                        },
                        "URL": {
                            "url": lead['url']
                        },
                        "Thread Number": {
                            "number": next_thread_number
                        },

                        "Status": {
                            "select": {
                                "name": "Contacted"
                            }
                        }
                    }
                )
                
                # Mark as sent and save thread number
                c.execute('UPDATE leads SET sent_to_notion = 1, notion_thread_number = ? WHERE id = ?', 
                         (next_thread_number, lead['id']))
                success_count += 1
                next_thread_number += 1  # Increment for next lead

                
            except Exception as e:
                error_count += 1
                errors.append(f"{lead['title'][:50]}: {str(e)}")
                print(f"Error sending lead {lead['id']} to Notion: {e}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Sent {success_count} leads to Notion',
            'count': success_count,
            'errors': error_count,
            'error_details': errors if errors else None
        })
        
    except Exception as e:
        print(f"Error in bulk send: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notion/status/<lead_id>')
def get_notion_status(lead_id):
    """Check if a lead has been sent to Notion"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT sent_to_notion, notion_thread_number FROM leads WHERE id = ?', (lead_id,))
        lead = c.fetchone()
        conn.close()
        
        if not lead:
            return jsonify({'success': False, 'error': 'Lead not found'}), 404
        
        return jsonify({
            'success': True,
            'sent_to_notion': lead['sent_to_notion'] == 1,
            'thread_number': lead['notion_thread_number']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# START SERVER
# ============================================

if __name__ == '__main__':
    print("StatusMonkey Lead Finder Starting...")
    print("Dashboard: http://localhost:5000")
    print("NEW: Notion Integration + Thread Numbers!")

    app.run(debug=True, port=5000)
