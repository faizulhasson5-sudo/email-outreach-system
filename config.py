import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent
load_dotenv(project_root / '.env')

class Config:
    # SMTP Settings
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
    SENDER_NAME = os.getenv('SENDER_NAME', 'Web Design Services')

    # Database
    DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///data/leads.db')

    # Scraping Settings
    MAX_LEADS_PER_SEARCH = int(os.getenv('MAX_LEADS_PER_SEARCH', 100))
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', 2.0))  # seconds between requests
    USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    # Email Sending
    EMAILS_PER_DAY = int(os.getenv('EMAILS_PER_DAY', 100))
    EMAIL_DELAY = float(os.getenv('EMAIL_DELAY', 30.0))  # seconds between emails
    TRACKING_ENABLED = os.getenv('TRACKING_ENABLED', 'True').lower() == 'true'

    # Tracking Server
    TRACKING_DOMAIN = os.getenv('TRACKING_DOMAIN', 'http://localhost:5000')

    # Business Categories
    BUSINESS_CATEGORIES = [
        'restaurants', 'dentists', 'plumbers', 'electricians',
        'landscaping', 'cleaning services', 'auto repair',
        'real estate agents', 'lawyers', 'accountants',
        'gyms', 'salons', 'spas', 'photographers',
        'roofers', 'painters', 'movers', 'HVAC'
    ]

    # Target Locations (add your target cities/areas)
    TARGET_LOCATIONS = [
        'New York, NY',
        'Los Angeles, CA',
        'Chicago, IL',
        'Houston, TX',
        'Phoenix, AZ'
    ]

    # Email Templates Directory
    TEMPLATES_DIR = 'templates'

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/email_outreach.log'
