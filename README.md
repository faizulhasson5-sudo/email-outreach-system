# Email Outreach System

A complete Python-based email outreach system for web designers to find and contact businesses that need website improvements.

## Features

### Lead Generation
- **Google Maps Scraping**: Find businesses by category and location
- **Yelp Integration**: Extract business listings from Yelp
- **Business Directories**: Scrape YellowPages, Manta, and other directories
- **CSV Import**: Import leads from CSV files

### Email Management
- **Email Extraction**: Automatically find emails from business websites
- **Email Verification**: Verify emails using DNS/MX records
- **Website Analysis**: Analyze website quality to identify businesses needing help
- **Personalized Templates**: Business-type specific email templates

### Email Sending
- **SMTP Integration**: Send via Gmail, Outlook, or any SMTP server
- **Batch Sending**: Send hundreds of emails with configurable delays
- **Rate Limiting**: Respect email provider limits
- **Campaign Management**: Organize sends into campaigns

### Tracking & Analytics
- **Open Tracking**: Track when emails are opened
- **Click Tracking**: Track link clicks
- **Reply Detection**: Monitor responses
- **Analytics Dashboard**: Visualize your outreach performance

### Web Dashboard
- **Lead Management**: View, add, edit, and delete leads
- **Campaign Control**: Create and manage email campaigns
- **Template Editor**: Create and customize email templates
- **Real-time Stats**: Monitor opens, clicks, and replies
- **Settings**: Configure SMTP and system settings

## Quick Start

### 1. Setup

```bash
cd email-outreach-system
python setup.py
```

This will:
- Create a virtual environment
- Install all dependencies
- Create the database
- Load default templates
- Create configuration file

### 2. Configure SMTP

Edit the `.env` file with your email credentials:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Your Name
```

**For Gmail users**: You need to generate an App Password:
1. Go to https://myaccount.google.com/apppasswords
2. Generate an app password for "Mail"
3. Use this password in your .env file

### 3. Start the System

**Option A: Command Line Interface**
```bash
python main.py
```

**Option B: Web Dashboard**
```bash
python -m dashboard.app
```

Then open http://localhost:5000 in your browser.

## Usage

### Scraping Leads

1. Go to Scraping in the dashboard
2. Select a source (Google Maps, Yelp, or Directories)
3. Enter business category and location
4. Click "Start Scraping"

### Extracting Emails

1. The system will automatically find emails from lead websites
2. Or run from CLI: Choose option 3 in main menu

### Sending Emails

1. Go to Leads in the dashboard
2. Select leads with verified emails
3. Click "Send to Selected"
4. Or create a campaign for batch sending

### Managing Templates

1. Go to Templates in the dashboard
2. Create custom templates using variables:
   - `{{ business_name }}` - Business name
   - `{{ city }}` - Business city
   - `{{ benefits }}` - List of benefits
   - `{{ greeting }}` - Personalized greeting
   - `{{ cta_text }}` - Call-to-action

## Project Structure

```
email-outreach-system/
├── main.py                 # CLI interface
├── setup.py               # Setup script
├── config.py              # Configuration
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── scrapers/             # Lead scraping modules
│   ├── google_maps.py   # Google Maps scraper
│   └── __init__.py
├── email_engine/         # Email processing
│   ├── extractor.py     # Email extraction & verification
│   ├── personalizer.py  # Email personalization
│   ├── sender.py        # SMTP sender with tracking
│   └── __init__.py
├── database/             # Database models
│   ├── models.py        # SQLAlchemy models
│   └── __init__.py
├── dashboard/            # Web dashboard
│   ├── app.py           # Flask application
│   └── templates/       # HTML templates
├── templates/           # Email templates
├── data/               # Database files
├── logs/               # System logs
└── tracking/           # Tracking assets
```

## Email Templates

### Default Templates

The system includes templates for:
- Restaurants
- Dentists
- Plumbers
- Electricians
- Landscaping
- Cleaning Services
- Auto Repair
- And more...

### Creating Custom Templates

Use the template editor in the dashboard or create JSON files in the templates directory.

**Template Variables:**
- `{{ business_name }}` - Lead's business name
- `{{ business_type }}` - Type of business
- `{{ city }}` - Business location city
- `{{ state }}` - Business state
- `{{ benefits }}` - Array of benefits (loop with {% for benefit in benefits %})
- `{{ greeting }}` - Random greeting (Hi, Hello, Hey)
- `{{ cta_text }}` - Call-to-action text
- `{{ sender_name }}` - Your name from config
- `{{ sender_email }}` - Your email from config

## Configuration

### SMTP Settings

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Email Limits

```env
EMAILS_PER_DAY=100          # Max emails per day
EMAIL_DELAY=30.0            # Seconds between emails
REQUEST_DELAY=2.0           # Seconds between scrape requests
```

### Tracking

```env
TRACKING_ENABLED=True
TRACKING_DOMAIN=http://localhost:5000
```

## API Endpoints

### Dashboard Routes
- `GET /` - Dashboard home
- `GET /leads` - Leads management
- `GET /campaigns` - Campaign management
- `GET /templates` - Template management
- `GET /analytics` - Analytics dashboard
- `GET /settings` - System settings

### API Routes
- `GET /api/stats` - Get statistics
- `GET /api/leads` - Get all leads
- `POST /api/send` - Send emails to leads

### Tracking Routes
- `GET /track/open/<pixel_id>` - Track email opens
- `GET /track/click/<lead_id>` - Track link clicks

## Best Practices

### Email Deliverability

1. **Warm up your domain**: Start with small batches (10-20 emails) and gradually increase
2. **Use a dedicated sending domain**: Separate from your primary domain
3. **Monitor bounce rates**: Keep under 5%
4. **Include unsubscribe link**: Required by law (CAN-SPAM, GDPR)
5. **Personalize emails**: Avoid generic templates
6. **Send at optimal times**: Tuesday-Thursday, 10am-2pm

### Lead Quality

1. **Verify emails**: Always verify before sending
2. **Check website quality**: Focus on businesses with poor/no websites
3. **Target local businesses**: Easier to personalize and build trust
4. **Track engagement**: Focus on engaged leads

### Compliance

1. **CAN-SPAM Act**: Include physical address, unsubscribe option
2. **GDPR**: Get consent for EU contacts
3. **Provide value**: Don't just sell, help businesses improve
4. **Honor unsubscribe requests**: Immediately

## Troubleshooting

### SMTP Authentication Failed
- Check your email and password
- For Gmail, use App Password (not regular password)
- Enable "Less secure app access" (not recommended)

### No Emails Found
- Check if websites are accessible
- Some sites block scrapers
- Try different business categories

### Dashboard Not Loading
- Ensure port 5000 is not in use
- Check Flask is installed
- Look at logs for errors

## License

This software is for educational purposes. Use responsibly and in compliance with all applicable laws and regulations.
