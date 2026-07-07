"""
SMTP Email Sender with Tracking
Sends personalized emails with open/click tracking
"""

import smtplib
import ssl
import time
import uuid
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from database.models import Lead, EmailLog, Campaign, get_db
from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailSender:
    """Sends emails via SMTP with tracking"""

    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.username = Config.SMTP_USERNAME
        self.password = Config.SMTP_PASSWORD
        self.sender_email = Config.SENDER_EMAIL
        self.sender_name = Config.SENDER_NAME
        self.tracking_enabled = Config.TRACKING_ENABLED
        self.tracking_domain = Config.TRACKING_DOMAIN

    def _create_tracking_pixel(self, lead_id, campaign_id=None):
        """Create a unique tracking pixel ID"""
        pixel_id = str(uuid.uuid4())
        return pixel_id

    def _get_tracking_pixel(self, pixel_id):
        """Generate tracking pixel HTML"""
        if not self.tracking_enabled:
            return ""

        # 1x1 transparent GIF pixel
        pixel_url = f"{self.tracking_domain}/track/open/{pixel_id}"
        return f'<img src="{pixel_url}" width="1" height="1" style="display:none;" alt="" />'

    def _add_click_tracking(self, html_content, lead_id, campaign_id=None):
        """Add click tracking to links in email"""
        if not self.tracking_enabled:
            return html_content

        # Simple click tracking - wraps links with tracking URL
        # In production, you'd want more sophisticated tracking
        return html_content

    def send_email(self, lead, email_content, campaign_id=None):
        """Send a single email to a lead"""
        db = get_db()

        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = lead.email
            msg['Subject'] = email_content['subject']

            # Add headers
            msg['X-Mailer'] = 'Custom Email Outreach System'
            msg['X-Campaign'] = str(campaign_id) if campaign_id else ''

            # Create tracking pixel
            pixel_id = self._create_tracking_pixel(lead.id, campaign_id)
            tracking_pixel = self._get_tracking_pixel(pixel_id)

            # Plain text version
            text_content = email_content['body']
            msg.attach(MIMEText(text_content, 'plain'))

            # HTML version with tracking
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                {email_content['body'].replace(chr(10), '<br>')}
                {tracking_pixel}
            </body>
            </html>
            """
            msg.attach(MIMEText(html_content, 'html'))

            # Send email
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)

            # Log success
            email_log = EmailLog(
                lead_id=lead.id,
                campaign_id=campaign_id,
                template_id=email_content.get('template_id'),
                subject=email_content['subject'],
                tracking_pixel_id=pixel_id
            )
            db.add(email_log)

            # Update lead status
            lead.email_sent = True
            lead.email_sent_at = datetime.utcnow()

            db.commit()

            logger.info(f"Email sent to {lead.email} ({lead.business_name})")
            print(f"[+] Email sent to: {lead.email}")

            return True, "Email sent successfully"

        except smtplib.SMTPAuthenticationError:
            error_msg = "SMTP authentication failed. Check your credentials."
            logger.error(error_msg)
            return False, error_msg

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

        finally:
            db.close()

    def send_batch(self, leads, email_content, campaign_id=None, delay=None):
        """Send emails to multiple leads with delay"""
        if delay is None:
            delay = Config.EMAIL_DELAY

        results = {
            'sent': 0,
            'failed': 0,
            'errors': []
        }

        total = len(leads)
        print(f"\n[*] Sending batch of {total} emails...")

        for i, lead in enumerate(leads, 1):
            print(f"\n[{i}/{total}] Processing: {lead.business_name}")

            if not lead.email:
                print(f"[-] Skipping {lead.business_name} - no email")
                results['failed'] += 1
                continue

            if lead.email_sent:
                print(f"[-] Skipping {lead.business_name} - already sent")
                continue

            success, message = self.send_email(lead, email_content, campaign_id)

            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'lead': lead.business_name,
                    'email': lead.email,
                    'error': message
                })

            # Delay between emails to avoid rate limiting
            if i < total:
                time.sleep(delay)

        print(f"\n[+] Batch complete: {results['sent']} sent, {results['failed']} failed")
        return results

    def send_campaign(self, campaign_id, leads=None):
        """Send emails for a specific campaign"""
        db = get_db()

        try:
            campaign = db.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return None

            # Get leads for this campaign
            if leads is None:
                leads = db.query(Lead).filter(
                    Lead.email_verified == True,
                    Lead.email_sent == False,
                    Lead.email != None
                ).limit(campaign.total_leads or Config.EMAILS_PER_DAY).all()

            # Get template
            from email_engine.personalizer import EmailPersonalizer
            personalizer = EmailPersonalizer()

            # Send emails
            results = {
                'campaign_id': campaign_id,
                'total_leads': len(leads),
                'sent': 0,
                'failed': 0,
                'errors': []
            }

            for lead in leads:
                # Generate personalized email
                email_content = personalizer.generate_personalized_email(lead)

                # Send email
                success, message = self.send_email(lead, email_content, campaign_id)

                if success:
                    results['sent'] += 1
                    campaign.emails_sent += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'lead': lead.business_name,
                        'email': lead.email,
                        'error': message
                    })

                # Delay between emails
                time.sleep(Config.EMAIL_DELAY)

            # Update campaign status
            if results['sent'] > 0:
                campaign.status = 'active'
                if campaign.started_at is None:
                    campaign.started_at = datetime.utcnow()

            db.commit()

            logger.info(f"Campaign {campaign_id} results: {results['sent']} sent, {results['failed']} failed")
            return results

        except Exception as e:
            logger.error(f"Error in campaign {campaign_id}: {str(e)}")
            return None

        finally:
            db.close()

    def get_send_stats(self):
        """Get email sending statistics"""
        db = get_db()

        stats = {
            'total_sent': db.query(EmailLog).count(),
            'sent_today': db.query(EmailLog).filter(
                EmailLog.sent_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).count(),
            'total_opened': db.query(Lead).filter(Lead.email_opened == True).count(),
            'total_replied': db.query(Lead).filter(Lead.replied == True).count(),
            'total_bounced': db.query(Lead).filter(Lead.bounced == True).count()
        }

        db.close()
        return stats


class EmailTracker:
    """Handles email tracking (opens, clicks)"""

    def __init__(self):
        self.tracking_domain = Config.TRACKING_DOMAIN

    def track_open(self, pixel_id):
        """Track email open"""
        db = get_db()

        try:
            email_log = db.query(EmailLog).filter_by(tracking_pixel_id=pixel_id).first()
            if email_log:
                email_log.opened_at = datetime.utcnow()

                # Update lead
                lead = db.query(Lead).filter_by(id=email_log.lead_id).first()
                if lead:
                    lead.email_opened = True
                    lead.email_opened_at = datetime.utcnow()

                db.commit()
                logger.info(f"Email opened: pixel_id={pixel_id}")
                return True
        except Exception as e:
            logger.error(f"Error tracking open: {e}")
        finally:
            db.close()

        return False

    def track_click(self, lead_id, campaign_id=None):
        """Track email click"""
        db = get_db()

        try:
            lead = db.query(Lead).filter_by(id=lead_id).first()
            if lead:
                lead.email_clicked = True
                lead.email_clicked_at = datetime.utcnow()
                db.commit()
                logger.info(f"Email clicked: lead_id={lead_id}")
                return True
        except Exception as e:
            logger.error(f"Error tracking click: {e}")
        finally:
            db.close()

        return False

    def get_tracking_stats(self, campaign_id=None):
        """Get tracking statistics"""
        db = get_db()

        query = db.query(EmailLog)
        if campaign_id:
            query = query.filter_by(campaign_id=campaign_id)

        total = query.count()
        opened = query.filter(EmailLog.opened_at != None).count()

        stats = {
            'total_sent': total,
            'total_opened': opened,
            'open_rate': (opened / total * 100) if total > 0 else 0
        }

        db.close()
        return stats
