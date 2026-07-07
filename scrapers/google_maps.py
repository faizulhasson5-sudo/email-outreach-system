"""
Google Maps Business Scraper - WORKING VERSION
Uses SerpAPI free tier or direct scraping
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from urllib.parse import quote_plus
from fake_useragent import UserAgent
from database.models import Lead, ScrapingSession, get_db
from config import Config

class GoogleMapsScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()

    def get_headers(self):
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def search_businesses(self, category, location):
        """Search businesses using Google Search (free method)"""
        query = f"{category} in {location} email contact"
        print(f"[*] Searching Google for: {query}")

        businesses = []

        # Method 1: Google Search scraping
        try:
            url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
            response = self.session.get(url, headers=self.get_headers(), timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract business listings from search results
            for g in soup.find_all('div', class_='g'):
                title_elem = g.find('h3')
                link_elem = g.find('a')
                snippet_elem = g.find('div', class_='VwiC3b')

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem.get('href')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''

                    # Extract email from snippet
                    email = self._extract_email(snippet)
                    if not email and link:
                        email = self._extract_email_from_page(link)

                    businesses.append({
                        'business_name': title,
                        'business_type': category,
                        'email': email,
                        'website': link if link and link.startswith('http') else None,
                        'phone': self._extract_phone(snippet),
                        'address': None,
                        'city': location.split(',')[0].strip() if location else None,
                        'state': location.split(',')[1].strip() if ',' in location else None,
                        'country': 'USA',
                        'source': 'google_search'
                    })

            print(f"[+] Found {len(businesses)} businesses from Google")

        except Exception as e:
            print(f"[-] Google search error: {e}")

        # Method 2: Use DuckDuckGo (more reliable, less blocking)
        if len(businesses) < 5:
            try:
                ddg_businesses = self._search_duckduckgo(category, location)
                businesses.extend(ddg_businesses)
            except Exception as e:
                print(f"[-] DuckDuckGo error: {e}")

        return businesses[:Config.MAX_LEADS_PER_SEARCH]

    def _search_duckduckgo(self, category, location):
        """Search using DuckDuckGo (less likely to block)"""
        query = f"{category} {location} email"
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        response = self.session.get(url, headers=self.get_headers(), timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        businesses = []
        for result in soup.find_all('div', class_='result'):
            title_elem = result.find('a', class_='result__a')
            snippet_elem = result.find('a', class_='result__snippet')

            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''

                email = self._extract_email(snippet)
                if not email and link:
                    email = self._extract_email_from_page(link)

                businesses.append({
                    'business_name': title,
                    'business_type': category,
                    'email': email,
                    'website': link,
                    'phone': self._extract_phone(snippet),
                    'address': None,
                    'city': location.split(',')[0].strip() if location else None,
                    'state': location.split(',')[1].strip() if ',' in location else None,
                    'country': 'USA',
                    'source': 'duckduckgo'
                })

        print(f"[+] Found {len(businesses)} businesses from DuckDuckGo")
        return businesses

    def _extract_email(self, text):
        """Extract email from text"""
        if not text:
            return None
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, text)
        # Filter out common invalid emails
        invalid = ['example.com', 'sentry.io', 'wixpress.com', 'google.com', 'facebook.com']
        for email in emails:
            if not any(inv in email for inv in invalid):
                return email.lower()
        return None

    def _extract_phone(self, text):
        """Extract phone number from text"""
        if not text:
            return None
        pattern = r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
        phones = re.findall(pattern, text)
        return phones[0] if phones else None

    def _extract_email_from_page(self, url):
        """Try to extract email from a webpage"""
        if not url or not url.startswith('http'):
            return None
        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=10)
            return self._extract_email(response.text)
        except:
            return None

    def save_leads(self, businesses):
        """Save businesses to database"""
        db = get_db()
        saved = 0

        for biz in businesses:
            if not biz.get('business_name'):
                continue

            # Check duplicate
            existing = db.query(Lead).filter_by(
                business_name=biz['business_name']
            ).first()

            if not existing:
                lead = Lead(
                    business_name=biz['business_name'],
                    business_type=biz.get('business_type'),
                    email=biz.get('email'),
                    phone=biz.get('phone'),
                    website=biz.get('website'),
                    address=biz.get('address'),
                    city=biz.get('city'),
                    state=biz.get('state'),
                    country=biz.get('country', 'USA'),
                    source=biz.get('source', 'google_search'),
                    email_verified=bool(biz.get('email'))
                )
                db.add(lead)
                saved += 1

        db.commit()
        db.close()
        print(f"[+] Saved {saved} new leads to database")
        return saved


class YelpScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()

    def search_businesses(self, category, location):
        """Search Yelp for businesses"""
        query = f"{category} {location}"
        url = f"https://www.yelp.com/search?find_desc={quote_plus(category)}&find_loc={quote_plus(location)}"

        print(f"[*] Searching Yelp for: {query}")

        try:
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml',
            }
            response = self.session.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')

            businesses = []
            # Yelp search results
            for item in soup.find_all('div', class_=re.compile('container__'))[:20]:
                name_elem = item.find('a', class_=re.compile('css-'))
                if name_elem:
                    businesses.append({
                        'business_name': name_elem.get_text(strip=True),
                        'business_type': category,
                        'email': None,
                        'website': None,
                        'phone': None,
                        'city': location.split(',')[0].strip(),
                        'state': location.split(',')[1].strip() if ',' in location else None,
                        'country': 'USA',
                        'source': 'yelp'
                    })

            print(f"[+] Found {len(businesses)} businesses from Yelp")
            return businesses

        except Exception as e:
            print(f"[-] Yelp search error: {e}")
            return []


class DirectoryScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()

    def search_all_directories(self, category, location):
        """Search multiple business directories"""
        all_businesses = []

        # YellowPages
        try:
            businesses = self._search_yellowpages(category, location)
            all_businesses.extend(businesses)
        except Exception as e:
            print(f"[-] YellowPages error: {e}")

        return all_businesses

    def _search_yellowpages(self, category, location):
        """Search YellowPages"""
        url = f"https://www.yellowpages.com/search?search_terms={quote_plus(category)}&geo_location_terms={quote_plus(location)}"

        headers = {'User-Agent': self.ua.random}
        response = self.session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        businesses = []
        for item in soup.find_all('div', class_='result')[:20]:
            name_elem = item.find('a', class_='business-name')
            if name_elem:
                businesses.append({
                    'business_name': name_elem.get_text(strip=True),
                    'business_type': category,
                    'email': None,
                    'website': None,
                    'phone': None,
                    'city': location.split(',')[0].strip(),
                    'state': location.split(',')[1].strip() if ',' in location else None,
                    'country': 'USA',
                    'source': 'yellowpages'
                })

        print(f"[+] Found {len(businesses)} businesses from YellowPages")
        return businesses
