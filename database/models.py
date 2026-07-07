from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import Config

Base = declarative_base()

class Lead(Base):
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True)
    business_name = Column(String(200), nullable=False)
    business_type = Column(String(100))
    email = Column(String(200))
    phone = Column(String(50))
    website = Column(String(500))
    website_quality = Column(String(50))  # 'none', 'poor', 'ai_generated', 'good'
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    country = Column(String(50))
    source = Column(String(100))  # 'google_maps', 'yelp', 'manual'
    scraped_at = Column(DateTime, default=datetime.utcnow)
    email_verified = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    email_opened = Column(Boolean, default=False)
    email_opened_at = Column(DateTime)
    email_clicked = Column(Boolean, default=False)
    email_clicked_at = Column(DateTime)
    replied = Column(Boolean, default=False)
    replied_at = Column(DateTime)
    bounced = Column(Boolean, default=False)
    notes = Column(Text)
    priority = Column(Integer, default=0)  # 0=normal, 1=high, 2=urgent

    def __repr__(self):
        return f"<Lead {self.business_name} - {self.email}>"

class EmailTemplate(Base):
    __tablename__ = 'email_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    business_type = Column(String(100))
    subject = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    times_used = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)

    def __repr__(self):
        return f"<Template {self.name}>"

class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    status = Column(String(50), default='draft')  # draft, active, paused, completed
    template_id = Column(Integer)
    total_leads = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_replied = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    def __repr__(self):
        return f"<Campaign {self.name}>"

class EmailLog(Base):
    __tablename__ = 'email_logs'

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, nullable=False)
    campaign_id = Column(Integer)
    template_id = Column(Integer)
    subject = Column(String(300))
    sent_at = Column(DateTime, default=datetime.utcnow)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    bounced = Column(Boolean, default=False)
    bounce_reason = Column(Text)
    tracking_pixel_id = Column(String(100))

    def __repr__(self):
        return f"<EmailLog Lead:{self.lead_id} Sent:{self.sent_at}>"

class ScrapingSession(Base):
    __tablename__ = 'scraping_sessions'

    id = Column(Integer, primary_key=True)
    source = Column(String(100))
    category = Column(String(100))
    location = Column(String(200))
    leads_found = Column(Integer, default=0)
    emails_found = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(50), default='running')

    def __repr__(self):
        return f"<ScrapingSession {self.source} - {self.category}>"


# Database initialization
engine = create_engine(Config.DATABASE_URI, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize database and create all tables"""
    Base.metadata.create_all(engine)
    print("[+] Database initialized successfully")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e
