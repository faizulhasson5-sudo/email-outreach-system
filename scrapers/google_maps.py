"""
Google Maps Business Scraper
Scrapes business listings from Google Maps search results
Uses requests + BeautifulSoup (free, no API key needed)
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
        self.base_url = "https://www.google.com/maps/search"

    def get_headers(self):
        """Generate random user agent headers"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def search_businesses(self, category, location):
        """Search for businesses on Google Maps"""
        query = f"{category} in {location}"
        encoded_query = quote_plus(query)
        url = f"{self.base_url}/{encoded_query}"

        print(f"[*] Searching: {query}")

        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            return self._parse_search_results(response.text, category, location)
        except requests.RequestException as e:
            print(f"[-] Error searching Google Maps: {e}")
            return []

    def _parse_search_results(self, html, category, location):
        """Parse business listings from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        businesses = []

        # Find business data in script tags (Google Maps embeds data in JSON)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'window._initData' in str(script.string):
                try:
                    # Extract JSON data from script
                    json_match = re.search(r'window._initData\s*=\s*({.*?});', str(script.string), re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        # Parse the nested structure for business listings
                        businesses.extend(self._extract_businesses_from_json(data, category, location))
                except (json.JSONDecodeError, Exception) as e:
                    print(f"[-] Error parsing JSON data: {e}")

        # Fallback: Try to find business cards in HTML
        if not businesses:
            business_cards = soup.find_all('div', {'class': re.compile(r'Nv2PK|section-result')})
            for card in business_cards[:Config.MAX_LEADS_PER_SEARCH]:
                business = self._parse_business_card(card, category, location)
                if business:
                    businesses.append(business)

        return businesses

    def _extract_businesses_from_json(self, data, category, location):
        """Extract business information from JSON data"""
        businesses = []
        try:
            # Navigate through Google's data structure
            if 'd' in data:
                inner_data = data['d']
                # Find business entries
                entries = re.findall(r'\[.*?\["(.*?)".*?\]', str(inner_data))
                # This is simplified - real implementation needs to handle Google's specific format
                pass
        except Exception:
            pass
        return businesses

    def _parse_business_card(self, card, category, location):
        """Parse a single business card from HTML"""
        try:
            name_elem = card.find('div', {'class': 'qBF1Pd'})
            if not name_elem:
                name_elem = card.find('span', {'class': 'fontHeadlineSmall'})

            name = name_elem.get_text(strip=True) if name_elem else None
            if not name:
                return None

            # Try to find website URL
            website = None
            website_elem = card.find('a', {'class': 'https'})
            if website_elem:
                website = website_elem.get('href')

            # Try to find phone number
            phone = None
            phone_elem = card.find('span', {'class': 'UsdlK'})
            if phone_elem:
                phone = phone_elem.get_text(strip=True)

            # Try to find address
            address = None
            addr_elem = card.find('div', {'class': 'W4Efsd'})
            if addr_elem:
                address = addr_elem.get_text(strip=True)

            return {
                'business_name': name,
                'business_type': category,
                'website': website,
                'phone': phone,
                'address': address,
                'city': location.split(',')[0].strip() if location else None,
                'state': location.split(',')[1].strip() if ',' in location else None,
                'country': 'USA',
                'source': 'google_maps'
            }
        except Exception as e:
            print(f"[-] Error parsing business card: {e}")
            return None

    def save_leads(self, businesses):
        """Save scraped businesses to database"""
        db = get_db()
        session = ScrapingSession(
            source='google_maps',
            category=businesses[0]['business_type'] if businesses else 'unknown',
            location='multiple'
        )
        db.add(session)
        db.commit()

        saved_count = 0
        for business in businesses:
            # Check if lead already exists
            existing = db.query(Lead).filter_by(
                business_name=business['business_name'],
                business_type=business['business_type']
            ).first()

            if not existing:
                lead = Lead(
                    business_name=business['business_name'],
                    business_type=business['business_type'],
                    website=business.get('website'),
                    phone=business.get('phone'),
                    address=business.get('address'),
                    city=business.get('city'),
                    state=business.get('state'),
                    country=business.get('country'),
                    source=business.get('source', 'google_maps'),
                    website_quality='unknown' if business.get('website') else 'none'
                )
                db.add(lead)
                saved_count += 1

        db.commit()
        session.leads_found = saved_count
        session.status = 'completed'
        db.commit()
        db.close()

        print(f"[+] Saved {saved_count} new leads to database")
        return saved_count

    def run_search(self, categories=None, locations=None):
        """Run full search for all categories and locations"""
        if categories is None:
            categories = Config.BUSINESS_CATEGORIES
        if locations is None:
            locations = Config.TARGET_LOCATIONS

        all_businesses = []

        for location in locations:
            for category in categories:
                businesses = self.search_businesses(category, location)
                all_businesses.extend(businesses)

                # Respect rate limits
                time.sleep(Config.REQUEST_DELAY)

        # Save all found businesses
        if all_businesses:
            self.save_leads(all_businesses)

        return all_businesses


# Alternative: Free Yelp scraping (no API key needed)
class YelpScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.base_url = "https://www.yelp.com/search"

    def search_businesses(self, category, location):
        """Search for businesses on Yelp"""
        params = {
            'find_desc': category,
            'find_loc': location
        }
        headers = {'User-Agent': self.ua.random}

        try:
            response = self.session.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return self._parse_results(response.text, category, location)
        except requests.RequestException as e:
            print(f"[-] Error searching Yelp: {e}")
            return []

    def _parse_results(self, html, category, location):
        """Parse Yelp search results"""
        soup = BeautifulSoup(html, 'html.parser')
        businesses = []

        # Find business listings
        listings = soup.find_all('div', {'class': re.compile(r'businessName|container__')})

        for listing in listings[:Config.MAX_LEADS_PER_SEARCH]:
            try:
                name_elem = listing.find('a', {'class': re.compile(r'businessName|css-')})
                name = name_elem.get_text(strip=True) if name_elem else None

                if name:
                    businesses.append({
                        'business_name': name,
                        'business_type': category,
                        'website': None,  # Yelp doesn't show direct website
                        'phone': None,
                        'address': None,
                        'city': location.split(',')[0].strip(),
                        'state': location.split(',')[1].strip() if ',' in location else None,
                        'country': 'USA',
                        'source': 'yelp'
                    })
            except Exception:
                continue

        return businesses


# Free business directory scraper
class DirectoryScraper:
    """Scrapes free business directories like YellowPages, Manta, etc."""

    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.directories = [
            {
                'name': 'YellowPages',
                'url': 'https://www.yellowpages.com/search',
                'params': {'search_terms': '{query}', 'geo_location_terms': '{location}'}
            },
            {
                'name': 'Manta',
                'url': 'https://www.manta.com/search',
                'params': {'q': '{query}', 'pg': '1'}
            }
        ]

    def search_all_directories(self, category, location):
        """Search all configured directories"""
        all_businesses = []

        for directory in self.directories:
            businesses = self._search_directory(directory, category, location)
            all_businesses.extend(businesses)
            time.sleep(Config.REQUEST_DELAY)

        return all_businesses

    def _search_directory(self, directory, category, location):
        """Search a single directory"""
        try:
            query = f"{category} {location}"
            url = directory['url']

            params = {}
            for key, value in directory['params'].items():
                params[key] = value.format(query=query, location=location)

            headers = {'User-Agent': self.ua.random}
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            return self._parse_directory_results(response.text, directory['name'], category, location)
        except Exception as e:
            print(f"[-] Error searching {directory['name']}: {e}")
            return []

    def _parse_directory_results(self, html, directory_name, category, location):
        """Parse results from a business directory"""
        soup = BeautifulSoup(html, 'html.parser')
        businesses = []

        # Generic parsing for common directory structures
        listings = soup.find_all(['div', 'article'], {'class': re.compile(r'result|listing|business')})

        for listing in listings[:Config.MAX_LEADS_PER_SEARCH]:
            try:
                # Try to find business name
                name_elem = listing.find(['h2', 'h3', 'a'], {'class': re.compile(r'name|title|company')})
                name = name_elem.get_text(strip=True) if name_elem else None

                # Try to find website
                website = None
                website_elem = listing.find('a', {'class': re.compile(r'website|url')})
                if website_elem:
                    website = website_elem.get('href')

                # Try to find phone
                phone = None
                phone_elem = listing.find('span', {'class': re.compile(r'phone|telephone')})
                if phone_elem:
                    phone = phone_elem.get_text(strip=True)

                if name:
                    businesses.append({
                        'business_name': name,
                        'business_type': category,
                        'website': website,
                        'phone': phone,
                        'address': None,
                        'city': location.split(',')[0].strip(),
                        'state': location.split(',')[1].strip() if ',' in location else None,
                        'country': 'USA',
                        'source': directory_name.lower()
                    })
            except Exception:
                continue

        return businesses
