"""
SMTP Email Sender - WORKING VERSION
Actually sends emails via Gmail/Outlook SMTP
"""

import smtplib
import ssl
import time
import uuid
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from database.models import Lead, EmailLog, Campaign, get_db
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/email_outreach.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.username = Config.SMTP_USERNAME
        self.password = Config.SMTP_PASSWORD
        self.sender_email = Config.SENDER_EMAIL
        self.sender_name = Config.SENDER_NAME
        self.tracking_domain = Config.TRACKING_DOMAIN

    def test_connection(self):
        """Test SMTP connection"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
            print("[+] SMTP connection successful!")
            return True
        except Exception as e:
            print(f"[-] SMTP connection failed: {e}")
            return False

    def send_email(self, lead, email_content, campaign_id=None):
        """Send a single email"""
        db = get_db()

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = lead.email
            msg['Subject'] = email_content['subject']
            msg['Reply-To'] = self.sender_email

            # Plain text
            text_body = email_content['body']
            msg.attach(MIMEText(text_body, 'plain'))

            # HTML version
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px;">
                {email_content['body'].replace(chr(10), '<br>')}
            </body>
            </html>
            """
            msg.attach(MIMEText(html_body, 'html'))

            # Send via SMTP
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)

            # Log to database
            pixel_id = str(uuid.uuid4())
            email_log = EmailLog(
                lead_id=lead.id,
                campaign_id=campaign_id,
                template_id=email_content.get('template_id'),
                subject=email_content['subject'],
                tracking_pixel_id=pixel_id
            )
            db.add(email_log)

            lead.email_sent = True
            lead.email_sent_at = datetime.utcnow()
            db.commit()

            print(f"[+] EMAIL SENT to {lead.email} ({lead.business_name})")
            logger.info(f"Email sent to {lead.email}")
            return True, "Sent successfully"

        except smtplib.SMTPAuthenticationError:
            msg = "SMTP authentication failed. Check your App Password."
            print(f"[-] {msg}")
            return False, msg

        except smtplib.SMTPException as e:
            msg = f"SMTP error: {str(e)}"
            print(f"[-] {msg}")
            return False, msg

        except Exception as e:
            msg = f"Error: {str(e)}"
            print(f"[-] {msg}")
            return False, msg

        finally:
            db.close()

    def send_batch(self, leads, campaign_id=None):
        """Send emails to multiple leads"""
        results = {'sent': 0, 'failed': 0, 'errors': []}

        print(f"\n{'='*50}")
        print(f"   SENDING {len(leads)} EMAILS")
        print(f"{'='*50}\n")

        for i, lead in enumerate(leads, 1):
            if not lead.email:
                print(f"[{i}/{len(leads)}] SKIP - {lead.business_name} (no email)")
                results['failed'] += 1
                continue

            if lead.email_sent:
                print(f"[{i}/{len(leads)}] SKIP - {lead.business_name} (already sent)")
                continue

            print(f"[{i}/{len(leads)}] Sending to {lead.business_name}...")

            # Generate personalized email
            from email_engine.personalizer import EmailPersonalizer
            personalizer = EmailPersonalizer()
            email_content = personalizer.generate_personalized_email(lead)

            # Send
            success, message = self.send_email(lead, email_content, campaign_id)

            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({'lead': lead.business_name, 'error': message})

            # Delay between emails
            if i < len(leads):
                time.sleep(Config.EMAIL_DELAY)

        print(f"\n{'='*50}")
        print(f"   COMPLETE: {results['sent']} sent, {results['failed']} failed")
        print(f"{'='*50}\n")

        return results


class EmailTracker:
    def track_open(self, pixel_id):
        """Track email open"""
        db = get_db()
        try:
            email_log = db.query(EmailLog).filter_by(tracking_pixel_id=pixel_id).first()
            if email_log:
                email_log.opened_at = datetime.utcnow()
                lead = db.query(Lead).filter_by(id=email_log.lead_id).first()
                if lead:
                    lead.email_opened = True
                    lead.email_opened_at = datetime.utcnow()
                db.commit()
                return True
        except Exception as e:
            logger.error(f"Tracking error: {e}")
        finally:
            db.close()
        return False

    def track_click(self, lead_id):
        """Track email click"""
        db = get_db()
        try:
            lead = db.query(Lead).filter_by(id=lead_id).first()
            if lead:
                lead.email_clicked = True
                lead.email_clicked_at = datetime.utcnow()
                db.commit()
                return True
        except Exception as e:
            logger.error(f"Tracking error: {e}")
        finally:
            db.close()
        return False
