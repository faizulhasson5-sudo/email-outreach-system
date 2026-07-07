"""
Email Extraction and Verification Module
Extracts emails from websites and verifies their validity
"""

import re
import dns.resolver
import socket
import smtplib
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from database.models import Lead, get_db
from config import Config

class EmailExtractor:
    """Extracts email addresses from websites"""

    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.email_pattern = re.compile(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        )

    def extract_emails_from_website(self, url):
        """Extract all emails from a website"""
        emails = set()

        if not url:
            return list(emails)

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            # Get main page
            headers = {'User-Agent': self.ua.random}
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # Extract emails from main page
            page_emails = self.email_pattern.findall(response.text)
            emails.update(page_emails)

            # Parse HTML for links to common contact pages
            soup = BeautifulSoup(response.text, 'html.parser')
            contact_links = self._find_contact_links(soup, url)

            # Check contact pages for more emails
            for link in contact_links[:5]:  # Limit to 5 pages
                try:
                    resp = self.session.get(link, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        page_emails = self.email_pattern.findall(resp.text)
                        emails.update(page_emails)
                except Exception:
                    continue

        except requests.RequestException as e:
            print(f"[-] Error fetching {url}: {e}")

        # Filter out common invalid emails
        valid_emails = self._filter_emails(emails)
        return list(valid_emails)

    def _find_contact_links(self, soup, base_url):
        """Find contact/about page links"""
        contact_patterns = ['contact', 'about', 'support', 'help', 'team']
        links = set()

        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').lower()
            text = a_tag.get_text(strip=True).lower()

            if any(pattern in href or pattern in text for pattern in contact_patterns):
                full_url = urljoin(base_url, a_tag['href'])
                if full_url.startswith(base_url):
                    links.add(full_url)

        return list(links)

    def _filter_emails(self, emails):
        """Filter out invalid/common emails"""
        invalid_patterns = [
            r'.*@example\.com$',
            r'.*@sentry\.io$',
            r'.*@wixpress\.com$',
            r'.*@google\.com$',
            r'.*@facebook\.com$',
            r'.*@twitter\.com$',
            r'^noreply@',
            r'^no-reply@',
            r'^donotreply@',
            r'.*\.png$',
            r'.*\.jpg$',
            r'.*\.gif$',
        ]

        valid_emails = set()
        for email in emails:
            email = email.lower().strip()
            if not any(re.match(pattern, email) for pattern in invalid_patterns):
                valid_emails.add(email)

        return valid_emails

    def extract_emails_from_html(self, html_content):
        """Extract emails from raw HTML content"""
        return list(set(self.email_pattern.findall(html_content)))


class EmailVerifier:
    """Verifies email addresses using multiple methods"""

    def __init__(self):
        self.common_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'mail.com', 'protonmail.com'
        ]

    def verify_email(self, email):
        """Verify an email address"""
        result = {
            'email': email,
            'is_valid': False,
            'is_disposable': False,
            'is_business': False,
            'mx_found': False,
            'smtp_valid': False,
            'reason': ''
        }

        # Basic format check
        if not self._is_valid_format(email):
            result['reason'] = 'Invalid format'
            return result

        # Extract domain
        domain = email.split('@')[1]

        # Check if disposable
        if self._is_disposable(domain):
            result['is_disposable'] = True
            result['reason'] = 'Disposable email'
            return result

        # Check if business email
        if domain not in self.common_domains:
            result['is_business'] = True

        # Check MX records
        if self._check_mx_records(domain):
            result['mx_found'] = True
        else:
            result['reason'] = 'No MX records found'
            return result

        # SMTP verification (optional, can be aggressive)
        # result['smtp_valid'] = self._smtp_verify(email, domain)

        result['is_valid'] = result['mx_found']
        if result['is_valid']:
            result['reason'] = 'Valid email'

        return result

    def _is_valid_format(self, email):
        """Check basic email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _is_disposable(self, domain):
        """Check if domain is a disposable email provider"""
        disposable_domains = [
            'tempmail.com', 'throwaway.email', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com', 'trashmail.com',
            'fakeinbox.com', 'sharklasers.com', 'guerrillamailblock.com',
            'grr.la', 'dispostable.com', '10minutemail.com'
        ]
        return domain in disposable_domains

    def _check_mx_records(self, domain):
        """Check if domain has MX records"""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(mx_records) > 0
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return False
        except Exception:
            return False

    def _smtp_verify(self, email, domain):
        """Verify email via SMTP (use carefully, may be blocked)"""
        try:
            # Get MX record
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_host = str(mx_records[0].exchange).rstrip('.')

            # Connect to SMTP server
            smtp = smtplib.SMTP(timeout=10)
            smtp.connect(mx_host, 25)
            smtp.helo('verify@example.com')
            smtp.mail('verify@example.com')
            code, message = smtp.rcpt(email)
            smtp.quit()

            return code == 250
        except Exception:
            return False

    def batch_verify(self, emails):
        """Verify multiple emails"""
        results = []
        for email in emails:
            result = self.verify_email(email)
            results.append(result)
        return results


class WebsiteAnalyzer:
    """Analyzes websites to determine if they need improvement"""

    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()

    def analyze_website(self, url):
        """Analyze a website and determine quality"""
        result = {
            'url': url,
            'has_website': bool(url),
            'is_valid': False,
            'quality_score': 0,
            'issues': [],
            'is_ai_generated': False,
            'needs_redesign': False,
            'load_time': None
        }

        if not url:
            result['issues'].append('No website')
            result['quality_score'] = 0
            result['needs_redesign'] = True
            return result

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            headers = {'User-Agent': self.ua.random}
            import time
            start_time = time.time()
            response = self.session.get(url, headers=headers, timeout=15, verify=False)
            load_time = time.time() - start_time

            result['load_time'] = round(load_time, 2)
            result['is_valid'] = response.status_code == 200

            if not result['is_valid']:
                result['issues'].append(f'Status code: {response.status_code}')
                result['needs_redesign'] = True
                return result

            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for common website builder signatures
            result['is_ai_generated'] = self._check_ai_generated(response.text, soup)
            if result['is_ai_generated']:
                result['issues'].append('Possible AI-generated website')

            # Check for modern design elements
            quality_score = 100

            # Check for mobile responsiveness
            viewport = soup.find('meta', {'name': 'viewport'})
            if not viewport:
                quality_score -= 20
                result['issues'].append('Not mobile responsive')

            # Check for SSL
            if not url.startswith('https'):
                quality_score -= 15
                result['issues'].append('No SSL certificate')

            # Check load time
            if load_time > 3:
                quality_score -= 20
                result['issues'].append(f'Slow load time: {load_time}s')

            # Check for outdated frameworks
            outdated = ['jquery', 'bootstrap3', 'flash', 'wix', 'weebly', 'godaddy']
            content_lower = response.text.lower()
            for tech in outdated:
                if tech in content_lower:
                    quality_score -= 10
                    result['issues'].append(f'Outdated technology: {tech}')

            # Check for basic SEO
            title = soup.find('title')
            if not title or not title.get_text(strip=True):
                quality_score -= 10
                result['issues'].append('Missing title tag')

            meta_desc = soup.find('meta', {'name': 'description'})
            if not meta_desc:
                quality_score -= 5
                result['issues'].append('Missing meta description')

            # Check for images without alt text
            images = soup.find_all('img')
            no_alt_count = sum(1 for img in images if not img.get('alt'))
            if no_alt_count > 0:
                quality_score -= min(no_alt_count * 2, 15)
                result['issues'].append(f'{no_alt_count} images without alt text')

            result['quality_score'] = max(0, quality_score)
            result['needs_redesign'] = result['quality_score'] < 70

            return result

        except requests.RequestException as e:
            result['issues'].append(f'Error: {str(e)}')
            result['needs_redesign'] = True
            return result

    def _check_ai_generated(self, html_content, soup):
        """Check if website appears to be AI-generated"""
        ai_indicators = [
            'generated by ai',
            'powered by ai',
            'ai content',
            'chatgpt',
            'openai',
            'artificial intelligence',
            'template',
            'lorem ipsum'
        ]

        content_lower = html_content.lower()
        ai_count = sum(1 for indicator in ai_indicators if indicator in content_lower)

        # Check for generic templates
        generic_templates = [
            'wix.com', 'weebly.com', 'squarespace.com',
            'godaddy.com', 'wordpress.com'
        ]

        template_count = sum(1 for template in generic_templates if template in content_lower)

        return ai_count >= 2 or template_count >= 1

    def batch_analyze(self, websites):
        """Analyze multiple websites"""
        results = []
        for url in websites:
            result = self.analyze_website(url)
            results.append(result)
        return results


def extract_and_verify_leads(limit=100):
    """Main function to extract emails and verify leads"""
    db = get_db()

    # Get leads without verified emails
    leads = db.query(Lead).filter(
        Lead.email_verified == False,
        Lead.email == None
    ).limit(limit).all()

    extractor = EmailExtractor()
    verifier = EmailVerifier()
    analyzer = WebsiteAnalyzer()

    processed = 0
    for lead in leads:
        print(f"[*] Processing: {lead.business_name}")

        # Analyze website if exists
        if lead.website:
            analysis = analyzer.analyze_website(lead.website)
            if analysis['needs_redesign']:
                lead.priority = 1 if analysis['quality_score'] < 50 else 0

        # Extract emails from website
        if lead.website:
            emails = extractor.extract_emails_from_website(lead.website)
            if emails:
                # Use first valid email
                for email in emails:
                    verification = verifier.verify_email(email)
                    if verification['is_valid']:
                        lead.email = email
                        lead.email_verified = True
                        break

        # Try to find email from business name (common patterns)
        if not lead.email:
            # Generate common email patterns for later verification
            possible_emails = self._generate_email_patterns(lead.business_name)
            for email in possible_emails:
                verification = verifier.verify_email(email)
                if verification['is_valid']:
                    lead.email = email
                    lead.email_verified = True
                    break

        db.commit()
        processed += 1

    db.close()
    print(f"[+] Processed {processed} leads")
    return processed

def _generate_email_patterns(business_name):
    """Generate common email patterns from business name"""
    # Convert business name to domain-like format
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
    domain = clean_name + '.com'

    patterns = [
        f'info@{domain}',
        f'contact@{domain}',
        f'hello@{domain}',
        f'support@{domain}',
        f'admin@{domain}',
        f'office@{domain}'
    ]

    return patterns
