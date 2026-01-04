from flask import Flask, render_template, jsonify, request
import requests
import time
import json
from datetime import datetime
import os

app = Flask(__name__)

# Data file to store leads
DATA_FILE = 'data/leads.json'

# Keywords for StatusMonkey.co lead generation
KEYWORDS = {
    'high_priority': [
        'website monitoring', 'uptime monitoring', 'server monitoring',
        'status page', 'downtime alert', 'website down', 'site monitoring',
        'uptime checker', 'ping monitoring', 'website availability'
    ],
    'competitors': [
        'pingdom', 'uptimerobot', 'statuspage', 'better uptime',
        'freshping', 'statuscake', 'site24x7'
    ],
    'pain_points': [
        'too expensive', 'looking for alternative', 'cheaper option',
        'need monitoring', 'recommend monitoring', 'downtime issues'
    ]
}

# Target subreddits
TARGET_SUBREDDITS = [
    'webdev', 'devops', 'sysadmin', 'startups', 'SaaS',
    'Entrepreneur', 'smallbusiness', 'webhosting', 'aws'
]

def load_leads():
    """Load leads from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'leads': [], 'keywords': KEYWORDS, 'subreddits': TARGET_SUBREDDITS}

def save_leads(data):
    """Save leads to JSON file"""
    os.makedirs('data', exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def score_lead(post):
    """Score lead based on keywords and context"""
    text = (post['title'] + ' ' + post.get('text', '')).lower()
    score = 0
    matched_keywords = []
    
    # High priority keywords
    for keyword in KEYWORDS['high_priority']:
        if keyword in text:
            score += 10
            matched_keywords.append(keyword)
    
    # Competitor mentions
    for competitor in KEYWORDS['competitors']:
        if competitor in text:
            score += 5
            matched_keywords.append(f"competitor:{competitor}")
    
    # Pain points (very valuable!)
    for pain in KEYWORDS['pain_points']:
        if pain in text:
            score += 15
            matched_keywords.append(f"pain:{pain}")
    
    # Determine priority
    if score >= 20:
        priority = 'hot'
    elif score >= 10:
        priority = 'warm'
    else:
        priority = 'cold'
    
    return {
        'score': score,
        'priority': priority,
        'matched_keywords': matched_keywords
    }

def fetch_reddit_posts(subreddit, limit=25):
    """Fetch posts from a subreddit"""
    url = f'https://www.reddit.com/r/{subreddit}/new/.json?limit={limit}'
    headers = {'User-Agent': 'StatusMonkeyFinder/1.0'}
    
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
    data = load_leads()
    existing_ids = {lead['id'] for lead in data['leads']}
    new_leads = []
    
    for subreddit in data['subreddits']:
        print(f"Scanning r/{subreddit}...")
        posts = fetch_reddit_posts(subreddit, limit=50)
        
        for post in posts:
            # Skip if already processed
            if post['id'] in existing_ids:
                continue
            
            # Check if post matches any keywords
            lead_info = score_lead(post)
            
            if lead_info['score'] > 0:
                lead = {
                    **post,
                    **lead_info,
                    'status': 'new',
                    'notes': '',
                    'found_at': datetime.now().isoformat()
                }
                new_leads.append(lead)
                data['leads'].insert(0, lead)  # Add to beginning
        
        time.sleep(2)  # Rate limiting
    
    save_leads(data)
    return len(new_leads)

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/leads')
def get_leads():
    """Get all leads"""
    data = load_leads()
    return jsonify(data['leads'])

@app.route('/api/scan', methods=['POST'])
def scan():
    """Trigger new scan"""
    new_count = scan_reddit()
    return jsonify({'success': True, 'new_leads': new_count})

@app.route('/api/lead/<lead_id>', methods=['PUT'])
def update_lead(lead_id):
    """Update lead status or notes"""
    data = load_leads()
    update = request.json
    
    for lead in data['leads']:
        if lead['id'] == lead_id:
            if 'status' in update:
                lead['status'] = update['status']
            if 'notes' in update:
                lead['notes'] = update['notes']
            break
    
    save_leads(data)
    return jsonify({'success': True})

@app.route('/api/stats')
def get_stats():
    """Get analytics stats"""
    data = load_leads()
    leads = data['leads']
    
    # Calculate stats
    total = len(leads)
    hot = len([l for l in leads if l['priority'] == 'hot'])
    warm = len([l for l in leads if l['priority'] == 'warm'])
    cold = len([l for l in leads if l['priority'] == 'cold'])
    
    contacted = len([l for l in leads if l['status'] == 'contacted'])
    converted = len([l for l in leads if l['status'] == 'converted'])
    
    # Top subreddits
    subreddit_counts = {}
    for lead in leads:
        sub = lead['subreddit']
        subreddit_counts[sub] = subreddit_counts.get(sub, 0) + 1
    
    top_subreddits = sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return jsonify({
        'total': total,
        'hot': hot,
        'warm': warm,
        'cold': cold,
        'contacted': contacted,
        'converted': converted,
        'top_subreddits': top_subreddits
    })

@app.route('/api/keywords')
def get_keywords():
    """Get current keywords"""
    data = load_leads()
    return jsonify(data.get('keywords', KEYWORDS))

@app.route('/api/subreddits')
def get_subreddits():
    """Get monitored subreddits"""
    data = load_leads()
    return jsonify(data.get('subreddits', TARGET_SUBREDDITS))

if __name__ == '__main__':
    print("🚀 StatusMonkey Lead Finder Starting...")
    print("📊 Dashboard: http://localhost:5000")
    app.run(debug=True, port=5000)
