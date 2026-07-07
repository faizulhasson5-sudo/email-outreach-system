"""
Email Personalization Engine
Creates personalized emails based on business type and needs
"""

import random
from datetime import datetime
from jinja2 import Template
from database.models import EmailTemplate, get_db
from config import Config

class EmailPersonalizer:
    """Creates personalized cold emails for web design services"""

    def __init__(self):
        self.business_benefits = {
            'restaurants': [
                'Online ordering system to increase sales',
                'Professional menu showcase with photos',
                'Reservation system integration',
                'Google Maps visibility for local searches',
                'Mobile-friendly design for on-the-go customers'
            ],
            'dentists': [
                'Online appointment booking system',
                'Patient education content showcase',
                'Before/after gallery for procedures',
                'Insurance information pages',
                'Professional credibility and trust building'
            ],
            'plumbers': [
                'Service area visibility on Google',
                'Online quote request forms',
                'Emergency service landing pages',
                'Customer testimonials showcase',
                'Before/after project galleries'
            ],
            'electricians': [
                'Service catalog with pricing',
                'Online scheduling system',
                'Safety tips and blog content',
                'License and certification display',
                'Emergency contact prominent placement'
            ],
            'landscaping': [
                'Portfolio showcase with before/after',
                'Seasonal service promotions',
                'Online estimate requests',
                'Service area mapping',
                'Maintenance schedule booking'
            ],
            'cleaning services': [
                'Online booking system',
                'Service packages display',
                'Customer reviews integration',
                'Before/after galleries',
                'Recurring service scheduling'
            ],
            'auto repair': [
                'Service menu with pricing',
                'Online appointment scheduling',
                'Vehicle-specific service pages',
                'Customer portal for history',
                'Parts ordering integration'
            ],
            'real estate agents': [
                'Property listing showcase',
                'Virtual tour integration',
                'Lead capture forms',
                'Neighborhood guides',
                'Market analysis pages'
            ],
            'lawyers': [
                'Practice area specialization pages',
                'Client testimonials (anonymized)',
                'Legal resource blog',
                'Case evaluation forms',
                'Attorney profile pages'
            ],
            'accountants': [
                'Service packages and pricing',
                'Tax deadline reminders',
                'Client portal integration',
                'Resource library',
                'Industry-specific solutions'
            ],
            'gyms': [
                'Class schedule integration',
                'Membership signup system',
                'Trainer profiles',
                'Virtual tour of facilities',
                'Progress tracking features'
            ],
            'salons': [
                'Online booking system',
                'Stylist portfolios',
                'Service menu with photos',
                'Product showcase',
                'Loyalty program integration'
            ],
            'spas': [
                'Treatment menu showcase',
                'Online reservation system',
                'Package deals display',
                'Gift certificate sales',
                'Wellness blog content'
            ],
            'photographers': [
                'Portfolio showcase',
                'Booking system',
                'Package pricing',
                'Client galleries',
                'Blog for behind-the-scenes'
            ],
            'roofers': [
                'Service area map',
                'Before/after galleries',
                'Emergency contact forms',
                'Insurance claim assistance',
                'Material comparison guides'
            ],
            'painters': [
                'Color consultation tools',
                'Project galleries',
                'Online estimate requests',
                'Seasonal promotions',
                'Interior design tips'
            ],
            'movers': [
                'Online quote calculator',
                'Service packages',
                'Moving checklist',
                'Storage solutions',
                'Customer reviews'
            ],
            'hvac': [
                'Emergency service prominence',
                'Maintenance plan signup',
                'Energy efficiency calculators',
                'Service area visibility',
                'Seasonal tips blog'
            ]
        }

        self.greeting_variations = [
            "Hi {name},",
            "Hello {name},",
            "Hey {name},",
            "Good morning {name},",
            "Good afternoon {name},"
        ]

        self.intros = [
            "I noticed your {business_type} business and wanted to reach out.",
            "I came across your {business_type} business and had an idea.",
            "As a {business_type} professional, you know how important first impressions are.",
            "I help {business_type} businesses like yours grow their online presence.",
            "Your {business_type} business caught my attention."
        ]

        self.closings = [
            "Best regards,",
            "Best,",
            "Thanks,",
            "Looking forward to hearing from you,",
            "Cheers,"
        ]

    def generate_personalized_email(self, lead, template_name=None):
        """Generate a personalized email for a lead"""
        db = get_db()

        # Get or create template
        if template_name:
            template = db.query(EmailTemplate).filter_by(name=template_name).first()
        else:
            template = db.query(EmailTemplate).filter_by(
                business_type=lead.business_type,
                is_active=True
            ).first()

        if not template:
            template = self._create_default_template(lead.business_type)
            db.add(template)
            db.commit()

        # Personalize the email
        personalized = self._personalize_template(template, lead)

        # Update template usage
        template.times_used += 1
        db.commit()
        db.close()

        return personalized

    def _personalize_template(self, template, lead):
        """Personalize a template with lead information"""
        # Get business-specific benefits
        benefits = self.business_benefits.get(
            lead.business_type.lower(),
            self.business_benefits.get('default', [
                'Professional online presence',
                'Increased customer trust',
                'Better search engine visibility',
                'Mobile-responsive design',
                'Lead generation capabilities'
            ])
        )

        # Select random elements for variation
        greeting = random.choice(self.greeting_variations).format(
            name=lead.business_name.split()[0] if lead.business_name else 'there'
        )

        # Create context for template
        context = {
            'greeting': greeting,
            'business_name': lead.business_name,
            'business_type': lead.business_type or 'business',
            'city': lead.city or 'your area',
            'benefits': random.sample(benefits, min(3, len(benefits))),
            'sender_name': Config.SENDER_NAME,
            'sender_email': Config.SENDER_EMAIL,
            'website_quality_note': self._get_quality_note(lead),
            'cta_text': self._get_cta_text(lead),
            'current_year': datetime.now().year
        }

        # Render template
        try:
            subject_template = Template(template.subject)
            body_template = Template(template.body)

            subject = subject_template.render(**context)
            body = body_template.render(**context)

            return {
                'subject': subject,
                'body': body,
                'template_id': template.id,
                'context': context
            }
        except Exception as e:
            print(f"[-] Error rendering template: {e}")
            return self._get_fallback_email(lead)

    def _get_quality_note(self, lead):
        """Generate note about website quality"""
        if lead.website_quality == 'none':
            return "I noticed you don't have a website yet"
        elif lead.website_quality == 'poor':
            return "I noticed your current website could use some improvement"
        elif lead.website_quality == 'ai_generated':
            return "I noticed your website appears to be template-based"
        else:
            return "I wanted to help enhance your online presence"

    def _get_cta_text(self, lead):
        """Generate call-to-action text"""
        cta_options = [
            "Would you be open to a quick 10-minute call to discuss how we can improve your online presence?",
            "I'd love to show you some examples of how we've helped similar businesses. Can I send you a quick portfolio?",
            "Would you be interested in a free website audit to see areas for improvement?",
            "Can I send you a custom proposal for your business?",
            "Would you like to see how your competitors' websites compare?"
        ]
        return random.choice(cta_options)

    def _create_default_template(self, business_type):
        """Create a default email template"""
        template = EmailTemplate(
            name=f"default_{business_type or 'general'}",
            business_type=business_type,
            subject="Quick question about {{ business_name }}'s online presence",
            body="""{{ greeting }}

{{ website_quality_note }}. As a web designer specializing in {{ business_type }} businesses, I've helped many companies in {{ city }} improve their online presence and attract more customers.

Here are some benefits a professional website can bring to {{ business_type }} businesses like yours:

{% for benefit in benefits %}
- {{ benefit }}
{% endfor %}

I'd love to discuss how we can help {{ business_type }} businesses like yours stand out online.

{{ cta_text }}

Best,
{{ sender_name }}
{{ sender_email }}
Web Design Services
"""
        )
        return template

    def _get_fallback_email(self, lead):
        """Get fallback email if template rendering fails"""
        return {
            'subject': f"Quick question about {lead.business_name}'s online presence",
            'body': f"""Hi there,

I noticed {lead.business_name} and wanted to reach out about your online presence.

As a web designer, I help businesses like yours create professional websites that attract more customers.

Would you be open to a quick chat about how we can improve your online presence?

Best,
{Config.SENDER_NAME}
{Config.SENDER_EMAIL}
""",
            'template_id': None,
            'context': {}
        }

    def create_template(self, name, business_type, subject, body):
        """Create a new email template"""
        db = get_db()

        template = EmailTemplate(
            name=name,
            business_type=business_type,
            subject=subject,
            body=body,
            is_active=True
        )

        db.add(template)
        db.commit()
        db.close()

        print(f"[+] Created template: {name}")
        return template

    def get_all_templates(self):
        """Get all active templates"""
        db = get_db()
        templates = db.query(EmailTemplate).filter_by(is_active=True).all()
        db.close()
        return templates

    def load_templates_from_file(self, filepath):
        """Load templates from a JSON file"""
        import json

        with open(filepath, 'r') as f:
            templates_data = json.load(f)

        db = get_db()
        for data in templates_data:
            template = EmailTemplate(
                name=data['name'],
                business_type=data.get('business_type'),
                subject=data['subject'],
                body=data['body'],
                is_active=True
            )
            db.add(template)

        db.commit()
        db.close()
        print(f"[+] Loaded {len(templates_data)} templates")
