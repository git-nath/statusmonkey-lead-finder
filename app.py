from flask import Flask, render_template, jsonify, request
import requests
import time
import json
from datetime import datetime
import os

app = Flask(__name__)

# Data file to store leads
DATA_FILE = 'data/leads.json'

# ENHANCED KEYWORDS for StatusMonkey.co lead generation
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

# Target subreddits with priority
TARGET_SUBREDDITS = {
    'high_priority': ['webdev', 'SaaS', 'startups', 'Entrepreneur', 'smallbusiness'],
    'medium_priority': ['selfhosted', 'sysadmin', 'webhosting', 'aws', 'devops']
}

# Reply templates
REPLY_TEMPLATES = {
    'downtime_issue': """Hey! I use StatusMonkey.co for this - it checks every 60 seconds and sends SMS alerts instantly. It's only $5.99/mo (free during beta). Has saved me multiple times! Here's my referral link: statusmonkey.co/?ref=reddit""",
    
    'competitor_complaint': """If you think [COMPETITOR] is expensive, check out StatusMonkey. $5.99/mo with 60-second checks, SMS alerts, AND a status page included. Currently free during beta: statusmonkey.co/?ref=reddit""",
    
    'recommendation': """I've been using StatusMonkey and it's been solid. 60-second monitoring, instant SMS/email alerts, and you get a status page. Best part? It's $5.99/mo and free during beta. Worth checking out: statusmonkey.co/?ref=reddit"""
}

def load_leads():
    """Load leads from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'leads': [], 
        'keywords': KEYWORDS, 
        'subreddits': TARGET_SUBREDDITS,
        'templates': REPLY_TEMPLATES
    }

def save_leads(data):
    """Save leads to JSON file"""
    os.makedirs('data', exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def score_lead(post):
    """Enhanced lead scoring for StatusMonkey"""
    text = (post['title'] + ' ' + post.get('text', '')).lower()
    score = 0
    matched_keywords = []
    priority = 'cold'
    suggested_template = 'recommendation'
    
    # EMERGENCY: Site is DOWN right now! (HOTTEST LEADS!)
    for keyword in KEYWORDS['urgent_leads']:
        if keyword in text:
            score += 50
            matched_keywords.append(f"🚨urgent:{keyword}")
            priority = 'emergency'
            suggested_template = 'downtime_issue'
    
    # Competitor complaints (Ready to switch!)
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
    
    # Budget keywords (Perfect for $5.99 pricing!)
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

def fetch_reddit_posts(subreddit, limit=50):
    """Fetch posts from a subreddit"""
    url = f'https://www.reddit.com/r/{subreddit}/new/.json?limit={limit}'
    headers = {'User-Agent': 'StatusMonkeyFinder/1.5'}
    
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
    
    # Scan high priority subreddits (handle both old and new format)
    subreddits_data = data.get('subreddits', TARGET_SUBREDDITS)
    if isinstance(subreddits_data, dict):
        all_subreddits = (
            subreddits_data.get('high_priority', []) + 
            subreddits_data.get('medium_priority', [])
        )
    else:
        # Old format - just use the list
        all_subreddits = subreddits_data
    
    for subreddit in all_subreddits:
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
                    'replied_at': None,
                    'converted': False,
                    'revenue': 0,
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
                if update['status'] == 'contacted':
                    lead['replied_at'] = datetime.now().isoformat()
            if 'notes' in update:
                lead['notes'] = update['notes']
            if 'converted' in update:
                lead['converted'] = update['converted']
                if update['converted']:
                    lead['revenue'] = 5.99  # StatusMonkey pricing
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
    emergency = len([l for l in leads if l['priority'] == 'emergency'])
    hot = len([l for l in leads if l['priority'] == 'hot'])
    warm = len([l for l in leads if l['priority'] == 'warm'])
    cold = len([l for l in leads if l['priority'] == 'cold'])
    
    contacted = len([l for l in leads if l['status'] == 'contacted'])
    converted = len([l for l in leads if l.get('converted', False)])
    revenue = sum(l.get('revenue', 0) for l in leads)
    
    # Top subreddits
    subreddit_counts = {}
    for lead in leads:
        sub = lead['subreddit']
        subreddit_counts[sub] = subreddit_counts.get(sub, 0) + 1
    
    top_subreddits = sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Conversion rate
    conversion_rate = (converted / contacted * 100) if contacted > 0 else 0
    
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
    data = load_leads()
    return jsonify(data.get('templates', REPLY_TEMPLATES))

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
# ADD THIS NEW ENDPOINT RIGHT BEFORE if __name__ == '__main__':

# ============================================
# TASK 26: Status update endpoint
# Purpose: Allow frontend to update lead status
# ============================================
@app.route('/update_status', methods=['POST'])
def update_status():
    try:
        data = request.json
        lead_id = data.get('lead_id')
        new_status = data.get('status')
        
        # Load current leads
        with open('data/leads.json', 'r') as f:
            all_leads = json.load(f)
        
        # Find and update the lead
        for lead in all_leads:
            if lead.get('id') == lead_id:
                lead['status'] = new_status
                # Add timestamp for when status changed
                lead['status_updated_at'] = datetime.now().isoformat()
                break
        
        # Save updated leads
        with open('data/leads.json', 'w') as f:
            json.dump(all_leads, f, indent=2)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 StatusMonkey Lead Finder v1.5 Starting...")
    print("📊 Dashboard: http://localhost:5000")
    print("✨ NEW: Emergency detection, reply templates, enhanced scoring!")
    app.run(debug=True, port=5000)
