"""
Web Dashboard for Email Outreach System
Flask-based dashboard for monitoring and managing campaigns
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from database.models import Lead, EmailTemplate, Campaign, EmailLog, ScrapingSession, get_db, init_db
from email_engine.sender import EmailSender, EmailTracker
from email_engine.personalizer import EmailPersonalizer
from config import Config
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

# System status file
STATUS_FILE = 'data/system_status.json'

def get_system_status():
    """Get system on/off status"""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    return {'running': False, 'paused_at': None}

def set_system_status(running):
    """Set system on/off status"""
    status = {
        'running': running,
        'paused_at': None if running else datetime.utcnow().isoformat(),
        'started_at': datetime.utcnow().isoformat() if running else None
    }
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f)
    return status

# Initialize database
init_db()

@app.route('/')
def index():
    """Dashboard home page"""
    db = get_db()

    # Get system status
    system_status = get_system_status()

    # Get statistics
    total_leads = db.query(Lead).count()
    leads_with_email = db.query(Lead).filter(Lead.email != None).count()
    emails_sent = db.query(Lead).filter(Lead.email_sent == True).count()
    emails_opened = db.query(Lead).filter(Lead.email_opened == True).count()
    emails_replied = db.query(Lead).filter(Lead.replied == True).count()

    # Recent activity
    recent_leads = db.query(Lead).order_by(Lead.scraped_at.desc()).limit(10).all()
    recent_campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).limit(5).all()

    db.close()

    return render_template('index.html',
        system_status=system_status,
        total_leads=total_leads,
        leads_with_email=leads_with_email,
        emails_sent=emails_sent,
        emails_opened=emails_opened,
        emails_replied=emails_replied,
        recent_leads=recent_leads,
        recent_campaigns=recent_campaigns
    )

@app.route('/leads')
def leads():
    """Leads management page"""
    db = get_db()

    page = request.args.get('page', 1, type=int)
    per_page = 50
    status = request.args.get('status', 'all')

    query = db.query(Lead)

    if status == 'no_email':
        query = query.filter(Lead.email == None)
    elif status == 'has_email':
        query = query.filter(Lead.email != None, Lead.email_sent == False)
    elif status == 'sent':
        query = query.filter(Lead.email_sent == True)
    elif status == 'opened':
        query = query.filter(Lead.email_opened == True)
    elif status == 'replied':
        query = query.filter(Lead.replied == True)

    total = query.count()
    leads_list = query.order_by(Lead.scraped_at.desc()).offset((page-1)*per_page).limit(per_page).all()

    db.close()

    return render_template('leads.html',
        leads=leads_list,
        total=total,
        page=page,
        per_page=per_page,
        status=status
    )

@app.route('/leads/add', methods=['POST'])
def add_lead():
    """Add a new lead"""
    db = get_db()

    lead = Lead(
        business_name=request.form.get('business_name'),
        business_type=request.form.get('business_type'),
        email=request.form.get('email'),
        phone=request.form.get('phone'),
        website=request.form.get('website'),
        address=request.form.get('address'),
        city=request.form.get('city'),
        state=request.form.get('state'),
        country=request.form.get('country', 'USA'),
        source='manual'
    )

    db.add(lead)
    db.commit()
    db.close()

    return redirect(url_for('leads'))

@app.route('/leads/delete/<int:lead_id>', methods=['POST'])
def delete_lead(lead_id):
    """Delete a lead"""
    db = get_db()
    lead = db.query(Lead).filter_by(id=lead_id).first()
    if lead:
        db.delete(lead)
        db.commit()
    db.close()
    return redirect(url_for('leads'))

@app.route('/campaigns')
def campaigns():
    """Campaigns page"""
    db = get_db()
    campaigns_list = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    db.close()
    return render_template('campaigns.html', campaigns=campaigns_list)

@app.route('/campaigns/create', methods=['POST'])
def create_campaign():
    """Create a new campaign"""
    db = get_db()

    campaign = Campaign(
        name=request.form.get('name'),
        template_id=request.form.get('template_id'),
        total_leads=request.form.get('total_leads', 100, type=int)
    )

    db.add(campaign)
    db.commit()
    db.close()

    return redirect(url_for('campaigns'))

@app.route('/campaigns/<int:campaign_id>/send', methods=['POST'])
def send_campaign(campaign_id):
    """Send emails for a campaign"""
    sender = EmailSender()
    results = sender.send_campaign(campaign_id)

    if results:
        return jsonify(results)
    return jsonify({'error': 'Failed to send campaign'}), 500

@app.route('/templates')
def templates():
    """Email templates page"""
    db = get_db()
    templates_list = db.query(EmailTemplate).order_by(EmailTemplate.created_at.desc()).all()
    db.close()
    return render_template('templates.html', templates=templates_list)

@app.route('/templates/create', methods=['POST'])
def create_template():
    """Create a new email template"""
    personalizer = EmailPersonalizer()
    template = personalizer.create_template(
        name=request.form.get('name'),
        business_type=request.form.get('business_type'),
        subject=request.form.get('subject'),
        body=request.form.get('body')
    )
    return redirect(url_for('templates'))

@app.route('/scraping')
def scraping():
    """Scraping management page"""
    db = get_db()
    sessions = db.query(ScrapingSession).order_by(ScrapingSession.started_at.desc()).limit(20).all()
    db.close()
    return render_template('scraping.html', sessions=sessions)

@app.route('/scraping/start', methods=['POST'])
def start_scraping():
    """Start a new scraping session"""
    from scrapers.google_maps import GoogleMapsScraper, YelpScraper, DirectoryScraper

    category = request.form.get('category')
    location = request.form.get('location')
    source = request.form.get('source', 'google_maps')

    print(f"\n[*] Starting scrape: {category} in {location} via {source}")

    businesses = []

    if source == 'google_maps':
        scraper = GoogleMapsScraper()
        businesses = scraper.search_businesses(category, location)
        if businesses:
            scraper.save_leads(businesses)
    elif source == 'yelp':
        scraper = YelpScraper()
        businesses = scraper.search_businesses(category, location)
    elif source == 'directory':
        scraper = DirectoryScraper()
        businesses = scraper.search_all_directories(category, location)

    # Save to database
    if businesses:
        db = get_db()
        for biz in businesses:
            if biz.get('business_name'):
                existing = db.query(Lead).filter_by(business_name=biz['business_name']).first()
                if not existing:
                    lead = Lead(
                        business_name=biz['business_name'],
                        business_type=biz.get('business_type', category),
                        email=biz.get('email'),
                        phone=biz.get('phone'),
                        website=biz.get('website'),
                        city=biz.get('city'),
                        state=biz.get('state'),
                        country='USA',
                        source=source
                    )
                    db.add(lead)
        db.commit()
        db.close()

    return jsonify({
        'status': 'completed',
        'found': len(businesses),
        'source': source,
        'category': category,
        'location': location
    })

@app.route('/analytics')
def analytics():
    """Analytics page"""
    db = get_db()

    # Get stats for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    daily_stats = []
    for i in range(30):
        date = thirty_days_ago + timedelta(days=i)
        next_date = date + timedelta(days=1)

        sent = db.query(EmailLog).filter(
            EmailLog.sent_at >= date,
            EmailLog.sent_at < next_date
        ).count()

        opened = db.query(Lead).filter(
            Lead.email_opened_at >= date,
            Lead.email_opened_at < next_date
        ).count()

        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'sent': sent,
            'opened': opened
        })

    # Overall stats
    total_sent = db.query(EmailLog).count()
    total_opened = db.query(Lead).filter(Lead.email_opened == True).count()
    total_replied = db.query(Lead).filter(Lead.replied == True).count()

    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0

    db.close()

    return render_template('analytics.html',
        daily_stats=daily_stats,
        total_sent=total_sent,
        total_opened=total_opened,
        total_replied=total_replied,
        open_rate=open_rate,
        reply_rate=reply_rate
    )

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', config=Config)

@app.route('/settings/save', methods=['POST'])
def save_settings():
    """Save settings to .env file"""
    env_content = f"""# SMTP Configuration
SMTP_SERVER={request.form.get('smtp_server', 'smtp.gmail.com')}
SMTP_PORT={request.form.get('smtp_port', 587)}
SMTP_USERNAME={request.form.get('smtp_username', '')}
SMTP_PASSWORD={request.form.get('smtp_password', '')}
SENDER_EMAIL={request.form.get('sender_email', '')}
SENDER_NAME={request.form.get('sender_name', '')}

# Database
DATABASE_URI=sqlite:///data/leads.db

# Scraping
MAX_LEADS_PER_SEARCH={request.form.get('max_leads', 100)}
REQUEST_DELAY={request.form.get('request_delay', 2.0)}

# Email Limits
EMAILS_PER_DAY={request.form.get('emails_per_day', 100)}
EMAIL_DELAY={request.form.get('email_delay', 30.0)}

# Tracking
TRACKING_ENABLED={request.form.get('tracking_enabled', 'True')}
TRACKING_DOMAIN={request.form.get('tracking_domain', 'http://localhost:5000')}
"""

    with open('.env', 'w') as f:
        f.write(env_content)

    return jsonify({'status': 'saved'})


# System Control Routes
@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start the email outreach system"""
    status = set_system_status(True)
    return jsonify({'status': 'started', 'data': status})

@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Stop/pause the email outreach system"""
    status = set_system_status(False)
    return jsonify({'status': 'stopped', 'data': status})

@app.route('/api/system/status')
def system_status():
    """Get current system status"""
    status = get_system_status()
    return jsonify(status)


# Tracking Routes
@app.route('/track/open/<pixel_id>')
def track_open(pixel_id):
    """Track email open"""
    tracker = EmailTracker()
    tracker.track_open(pixel_id)

    # Return 1x1 transparent GIF
    gif = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    return gif, 200, {'Content-Type': 'image/gif', 'Cache-Control': 'no-store, no-cache, must-revalidate'}

@app.route('/track/click/<int:lead_id>')
def track_click(lead_id):
    """Track email click"""
    tracker = EmailTracker()
    tracker.track_click(lead_id)

    # Redirect to target URL (you'd pass this as a parameter)
    return redirect('/')


# API Routes
@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    sender = EmailSender()
    stats = sender.get_send_stats()
    return jsonify(stats)

@app.route('/api/leads')
def api_leads():
    """API endpoint for leads"""
    db = get_db()
    leads = db.query(Lead).limit(100).all()
    db.close()

    return jsonify([{
        'id': lead.id,
        'business_name': lead.business_name,
        'business_type': lead.business_type,
        'email': lead.email,
        'website': lead.website,
        'email_sent': lead.email_sent,
        'email_opened': lead.email_opened
    } for lead in leads])

@app.route('/api/send', methods=['POST'])
def api_send():
    """API endpoint for sending emails"""
    data = request.json
    lead_ids = data.get('lead_ids', [])

    db = get_db()
    leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()

    if not leads:
        db.close()
        return jsonify({'error': 'No leads found'}), 404

    sender = EmailSender()

    # Test connection first
    if not sender.test_connection():
        db.close()
        return jsonify({'error': 'SMTP connection failed. Check your settings.'}), 500

    personalizer = EmailPersonalizer()
    results = []

    for lead in leads:
        if not lead.email:
            results.append({'lead_id': lead.id, 'success': False, 'message': 'No email'})
            continue

        if lead.email_sent:
            results.append({'lead_id': lead.id, 'success': False, 'message': 'Already sent'})
            continue

        email_content = personalizer.generate_personalized_email(lead)
        success, message = sender.send_email(lead, email_content)
        results.append({
            'lead_id': lead.id,
            'business_name': lead.business_name,
            'email': lead.email,
            'success': success,
            'message': message
        })

    db.close()

    sent_count = sum(1 for r in results if r['success'])
    return jsonify({
        'results': results,
        'sent': sent_count,
        'total': len(results)
    })


if __name__ == '__main__':
    print("\n" + "="*50)
    print("   Email Outreach System Dashboard")
    print("="*50)
    print(f"\n   Dashboard URL: http://localhost:5000")
    print(f"   Tracking Domain: {Config.TRACKING_DOMAIN}")
    print("\n" + "="*50 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
