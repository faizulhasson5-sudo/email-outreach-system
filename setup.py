"""
Setup Script for Email Outreach System
Automates initial setup and configuration
"""

import os
import sys
import shutil
from pathlib import Path

def print_banner():
    print("\n" + "="*50)
    print("   Email Outreach System Setup")
    print("="*50 + "\n")

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("[-] Python 3.8 or higher is required")
        sys.exit(1)
    print(f"[+] Python {sys.version_info.major}.{sys.version_info.minor} detected")

def create_virtual_environment():
    """Create Python virtual environment"""
    print("\n[*] Creating virtual environment...")

    venv_path = Path("venv")
    if venv_path.exists():
        print("[*] Virtual environment already exists")
        return

    os.system(f"{sys.executable} -m venv venv")
    print("[+] Virtual environment created")

    # Activate script for Windows
    activate_script = venv_path / "Scripts" / "activate.bat"
    if activate_script.exists():
        print(f"\n[*] To activate the virtual environment, run:")
        print(f"    {activate_script}")

def install_requirements():
    """Install Python packages"""
    print("\n[*] Installing requirements...")

    pip_path = Path("venv/Scripts/pip.exe") if os.name == 'nt' else Path("venv/bin/pip")
    if pip_path.exists():
        os.system(f'"{pip_path}" install -r requirements.txt')
    else:
        os.system(f"{sys.executable} -m pip install -r requirements.txt")

    print("[+] Requirements installed")

def create_env_file():
    """Create .env file from template"""
    print("\n[*] Creating configuration file...")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print("[*] .env file already exists")
        return

    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("[+] Created .env file from template")
        print("[!] Please edit .env file with your settings")
    else:
        # Create default .env
        default_env = """# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Your Name

# Database
DATABASE_URI=sqlite:///data/leads.db

# Scraping
MAX_LEADS_PER_SEARCH=100
REQUEST_DELAY=2.0

# Email Limits
EMAILS_PER_DAY=100
EMAIL_DELAY=30.0

# Tracking
TRACKING_ENABLED=True
TRACKING_DOMAIN=http://localhost:5000
"""
        with open('.env', 'w') as f:
            f.write(default_env)
        print("[+] Created default .env file")
        print("[!] Please edit .env file with your SMTP credentials")

def create_directories():
    """Create necessary directories"""
    print("\n[*] Creating directories...")

    directories = [
        "data",
        "logs",
        "templates",
        "dashboard/templates"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

    print("[+] Directories created")

def initialize_database():
    """Initialize the database"""
    print("\n[*] Initializing database...")

    sys.path.insert(0, os.getcwd())
    from database.models import init_db
    init_db()

    print("[+] Database initialized")

def load_default_templates():
    """Load default email templates"""
    print("\n[*] Loading default templates...")

    sys.path.insert(0, os.getcwd())
    from database.models import EmailTemplate, get_db

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

    print(f"[+] Loaded {len(default_templates)} default templates")

def print_next_steps():
    """Print next steps"""
    print("\n" + "="*50)
    print("   Setup Complete!")
    print("="*50)
    print("""
Next Steps:

1. Configure your SMTP settings:
   - Edit the .env file with your email credentials
   - For Gmail: Use an App Password (https://myaccount.google.com/apppasswords)

2. Start the system:
   python main.py

3. Or launch the web dashboard:
   python -m dashboard.app

4. Start scraping leads:
   - Use the dashboard or CLI to scrape businesses
   - Extract emails from their websites
   - Verify email addresses
   - Send personalized emails

5. Monitor your campaigns:
   - Track email opens and clicks
   - View analytics in the dashboard
   - Adjust your approach based on results

For help, see the README.md file.
""")

def main():
    """Main setup function"""
    print_banner()

    check_python_version()
    create_virtual_environment()
    create_directories()
    install_requirements()
    create_env_file()
    initialize_database()
    load_default_templates()
    print_next_steps()

    print("\n[+] Setup complete! Run 'python main.py' to start.\n")

if __name__ == '__main__':
    main()
