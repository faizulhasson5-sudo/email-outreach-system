"""
Email Outreach System - Main Runner
Command-line interface for managing the system
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import init_db, get_db, Lead, EmailTemplate, Campaign
from scrapers.google_maps import GoogleMapsScraper, YelpScraper, DirectoryScraper
from email_engine.extractor import EmailExtractor, EmailVerifier, WebsiteAnalyzer
from email_engine.personalizer import EmailPersonalizer
from email_engine.sender import EmailSender
from config import Config

def print_banner():
    """Print system banner"""
    print("\n" + "="*60)
    print("   EMAIL OUTREACH SYSTEM")
    print("   Web Design Lead Generation & Email Marketing")
    print("="*60 + "\n")

def print_menu():
    """Print main menu"""
    print("\nMAIN MENU:")
    print("1. Initialize Database")
    print("2. Scrape Leads")
    print("3. Extract Emails from Websites")
    print("4. Verify Emails")
    print("5. Send Emails")
    print("6. View Statistics")
    print("7. Manage Templates")
    print("8. Launch Dashboard")
    print("9. Import Leads from CSV")
    print("0. Exit")
    print()

def init_database():
    """Initialize the database"""
    print("\n[*] Initializing database...")
    init_db()
    print("[+] Database initialized successfully!")

def scrape_leads():
    """Scrape leads from various sources"""
    print("\nSCRAPING OPTIONS:")
    print("1. Google Maps")
    print("2. Yelp")
    print("3. Business Directories")
    print("4. All Sources")

    choice = input("\nSelect source (1-4): ")

    category = input("Enter business category (e.g., restaurants): ")
    location = input("Enter location (e.g., New York, NY): ")

    if choice == '1':
        scraper = GoogleMapsScraper()
        businesses = scraper.search_businesses(category, location)
        scraper.save_leads(businesses)
    elif choice == '2':
        scraper = YelpScraper()
        businesses = scraper.search_businesses(category, location)
        print(f"[+] Found {len(businesses)} businesses")
    elif choice == '3':
        scraper = DirectoryScraper()
        businesses = scraper.search_all_directories(category, location)
        print(f"[+] Found {len(businesses)} businesses")
    elif choice == '4':
        print("[*] Scraping from all sources...")
        all_businesses = []

        print("[*] Google Maps...")
        gm_scraper = GoogleMapsScraper()
        gm_businesses = gm_scraper.search_businesses(category, location)
        all_businesses.extend(gm_businesses)

        print("[*] Yelp...")
        yelp_scraper = YelpScraper()
        yelp_businesses = yelp_scraper.search_businesses(category, location)
        all_businesses.extend(yelp_businesses)

        print("[*] Directories...")
        dir_scraper = DirectoryScraper()
        dir_businesses = dir_scraper.search_all_directories(category, location)
        all_businesses.extend(dir_businesses)

        if all_businesses:
            gm_scraper.save_leads(all_businesses)

    print("[+] Scraping complete!")

def extract_emails():
    """Extract emails from lead websites"""
    print("\n[*] Extracting emails from websites...")

    db = get_db()
    leads = db.query(Lead).filter(
        Lead.website != None,
        Lead.email == None
    ).limit(50).all()

    if not leads:
        print("[-] No leads found for email extraction")
        db.close()
        return

    extractor = EmailExtractor()
    analyzer = WebsiteAnalyzer()

    for lead in leads:
        print(f"\n[*] Processing: {lead.business_name}")

        # Analyze website
        if lead.website:
            analysis = analyzer.analyze_website(lead.website)
            lead.website_quality = 'poor' if analysis['needs_redesign'] else 'good'
            print(f"    Website quality: {analysis['quality_score']}/100")

        # Extract emails
        emails = extractor.extract_emails_from_website(lead.website)
        if emails:
            lead.email = emails[0]
            print(f"    Found email: {emails[0]}")
        else:
            print("    No emails found")

        db.commit()

    db.close()
    print("\n[+] Email extraction complete!")

def verify_emails():
    """Verify email addresses"""
    print("\n[*] Verifying emails...")

    db = get_db()
    leads = db.query(Lead).filter(
        Lead.email != None,
        Lead.email_verified == False
    ).limit(50).all()

    if not leads:
        print("[-] No unverified emails found")
        db.close()
        return

    verifier = EmailVerifier()

    for lead in leads:
        print(f"\n[*] Verifying: {lead.email}")
        result = verifier.verify_email(lead.email)

        if result['is_valid']:
            lead.email_verified = True
            print(f"    [VALID] - Business: {result['is_business']}")
        else:
            print(f"    [INVALID] - {result['reason']}")

        db.commit()

    db.close()
    print("\n[+] Email verification complete!")

def send_emails():
    """Send emails to leads"""
    print("\nSEND EMAILS:")
    print("1. Send to all verified leads (no email sent)")
    print("2. Send to specific lead ID")
    print("3. Send test email")

    choice = input("\nSelect option (1-3): ")

    sender = EmailSender()
    personalizer = EmailPersonalizer()

    if choice == '1':
        db = get_db()
        leads = db.query(Lead).filter(
            Lead.email_verified == True,
            Lead.email_sent == False,
            Lead.email != None
        ).limit(Config.EMAILS_PER_DAY).all()

        if not leads:
            print("[-] No leads ready for email")
            db.close()
            return

        print(f"\n[*] Ready to send {len(leads)} emails")
        confirm = input("Confirm? (y/n): ")

        if confirm.lower() == 'y':
            for lead in leads:
                email_content = personalizer.generate_personalized_email(lead)
                sender.send_email(lead, email_content)

        db.close()

    elif choice == '2':
        lead_id = input("Enter lead ID: ")
        db = get_db()
        lead = db.query(Lead).filter_by(id=lead_id).first()

        if lead:
            email_content = personalizer.generate_personalized_email(lead)
            print(f"\nSubject: {email_content['subject']}")
            print(f"\nBody:\n{email_content['body']}")
            confirm = input("\nSend? (y/n): ")

            if confirm.lower() == 'y':
                sender.send_email(lead, email_content)
        else:
            print("[-] Lead not found")

        db.close()

    elif choice == '3':
        test_email = input("Enter test email address: ")
        test_name = input("Enter test business name: ")

        from database.models import Lead as LeadModel
        test_lead = LeadModel(
            business_name=test_name,
            business_type='restaurants',
            email=test_email,
            city='New York',
            state='NY'
        )

        email_content = personalizer.generate_personalized_email(test_lead)
        print(f"\nSubject: {email_content['subject']}")
        print(f"\nBody:\n{email_content['body']}")
        confirm = input("\nSend test email? (y/n): ")

        if confirm.lower() == 'y':
            sender.send_email(test_lead, email_content)

def view_statistics():
    """View system statistics"""
    db = get_db()

    total_leads = db.query(Lead).count()
    leads_with_email = db.query(Lead).filter(Lead.email != None).count()
    verified_emails = db.query(Lead).filter(Lead.email_verified == True).count()
    emails_sent = db.query(Lead).filter(Lead.email_sent == True).count()
    emails_opened = db.query(Lead).filter(Lead.email_opened == True).count()
    emails_replied = db.query(Lead).filter(Lead.replied == True).count()

    print("\n" + "="*40)
    print("   SYSTEM STATISTICS")
    print("="*40)
    print(f"   Total Leads:          {total_leads}")
    print(f"   Leads with Email:     {leads_with_email}")
    print(f"   Verified Emails:      {verified_emails}")
    print(f"   Emails Sent:          {emails_sent}")
    print(f"   Emails Opened:        {emails_opened}")
    print(f"   Emails Replied:       {emails_replied}")

    if emails_sent > 0:
        print(f"   Open Rate:            {emails_opened/emails_sent*100:.1f}%")
        print(f"   Reply Rate:           {emails_replied/emails_sent*100:.1f}%")

    print("="*40)

    db.close()

def manage_templates():
    """Manage email templates"""
    print("\nTEMPLATE MANAGEMENT:")
    print("1. View all templates")
    print("2. Create new template")
    print("3. Load default templates")

    choice = input("\nSelect option (1-3): ")

    if choice == '1':
        db = get_db()
        templates = db.query(EmailTemplate).all()

        if not templates:
            print("\n[-] No templates found")
        else:
            print("\nTEMPLATES:")
            for t in templates:
                print(f"  {t.id}. {t.name} ({t.business_type or 'general'}) - Used {t.times_used} times")

        db.close()

    elif choice == '2':
        name = input("Template name: ")
        business_type = input("Business type (or 'general'): ")
        subject = input("Subject line (use {{ variable }} for personalization): ")
        print("Body (use {{ variable }} for personalization, press Enter twice to finish):")
        body_lines = []
        empty_count = 0
        while empty_count < 2:
            line = input()
            if line == '':
                empty_count += 1
            else:
                empty_count = 0
                body_lines.append(line)
        body = '\n'.join(body_lines)

        personalizer = EmailPersonalizer()
        personalizer.create_template(name, business_type, subject, body)
        print("[+] Template created!")

    elif choice == '3':
        load_default_templates()

def load_default_templates():
    """Load default email templates"""
    default_templates = [
        {
            "name": "restaurants_default",
            "business_type": "restaurants",
            "subject": "Boost {{ business_name }}'s Online Ordering Revenue",
            "body": """{{ greeting }}

I noticed {{ business_name }} and wanted to reach out about your online presence.

Many restaurants in {{ city }} are missing out on significant revenue by not having a professional online ordering system. Here's how a modern website can help:

{% for benefit in benefits %}
- {{ benefit }}
{% endfor %}

I've helped restaurants increase their online orders by 40-60% with a professional website.

{{ cta_text }}

Best,
{{ sender_name }}
"""
        },
        {
            "name": "dentists_default",
            "business_type": "dentists",
            "subject": "Attract More Patients to {{ business_name }}",
            "body": """{{ greeting }}

I specialize in creating professional websites for dental practices like {{ business_name }}.

In today's digital world, patients research dentists online before booking. Here's what a modern website can do for your practice:

{% for benefit in benefits %}
- {{ benefit }}
{% endfor %}

Would you like to see how your competitors' websites compare?

Best,
{{ sender_name }}
"""
        },
        {
            "name": "contractors_default",
            "business_type": "contractors",
            "subject": "Get More Leads for {{ business_name }}",
            "body": """{{ greeting }}

I help contractors and home service businesses like {{ business_name }} generate more leads through professional websites.

Here are some benefits a modern website can bring:

{% for benefit in benefits %}
- {{ benefit }}
{% endfor %}

I'd love to show you some examples of how we've helped similar businesses.

{{ cta_text }}

Best,
{{ sender_name }}
"""
        }
    ]

    db = get_db()
    for data in default_templates:
        template = EmailTemplate(**data)
        db.add(template)
    db.commit()
    db.close()

    print(f"[+] Loaded {len(default_templates)} default templates!")

def launch_dashboard():
    """Launch the web dashboard"""
    print("\n[*] Starting dashboard server...")
    print("[*] Dashboard will be available at: http://localhost:5000")
    print("[*] Press Ctrl+C to stop\n")

    from dashboard.app import app
    app.run(debug=False, host='0.0.0.0', port=5000)

def import_csv():
    """Import leads from CSV file"""
    import csv

    filepath = input("Enter CSV file path: ")

    if not os.path.exists(filepath):
        print("[-] File not found")
        return

    db = get_db()
    imported = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lead = Lead(
                business_name=row.get('business_name', ''),
                business_type=row.get('business_type', ''),
                email=row.get('email', ''),
                phone=row.get('phone', ''),
                website=row.get('website', ''),
                city=row.get('city', ''),
                state=row.get('state', ''),
                country='USA',
                source='csv_import'
            )
            db.add(lead)
            imported += 1

    db.commit()
    db.close()

    print(f"[+] Imported {imported} leads from CSV")

def main():
    """Main function"""
    print_banner()

    while True:
        print_menu()
        choice = input("Enter your choice (0-9): ")

        if choice == '1':
            init_database()
        elif choice == '2':
            scrape_leads()
        elif choice == '3':
            extract_emails()
        elif choice == '4':
            verify_emails()
        elif choice == '5':
            send_emails()
        elif choice == '6':
            view_statistics()
        elif choice == '7':
            manage_templates()
        elif choice == '8':
            launch_dashboard()
        elif choice == '9':
            import_csv()
        elif choice == '0':
            print("\n[+] Goodbye!")
            sys.exit(0)
        else:
            print("[-] Invalid choice. Please try again.")

if __name__ == '__main__':
    main()
