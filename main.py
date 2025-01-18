from flask import Flask, request, jsonify
from celery_config import make_celery
from logger_config import configure_logging
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from flask_cors import CORS
import time
import threading
import logging

app = Flask(__name__)

# Enable CORS for the specific frontend domain
CORS(app, resources={r"/*": {"origins": "https://prcdrop.co.za"}})

# Configure Celery
celery = make_celery(app)

# Configure logging
configure_logging()
logging.info("Service started.")


# Setting up Chrome options for Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

# Utility function to load JSON data
def load_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading JSON file {file_path}: {e}")

selectors = load_json('price_selectors.json')
email_config = load_json('email_config.json')

# Normalize domain by stripping "www."
def normalize_domain(domain):
    if domain.startswith("www."):
        return domain[4:]  # Remove the first 4 characters ("www.")
    return domain

# Email function
def send_email(subject, body, sender_email, sender_password, receiver_email):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
    except Exception as e:
        logging.error(f"Error sending email: {e}")

# Price tracking function
def check_price(url, selectors):
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)

    domain = normalize_domain(urlparse(url).netloc)
    selector = selectors.get(domain)
    
    if not selector:
        logging.error(f"No selector found for {domain}")
        driver.quit()
        return None
    
    logging.info(f"Using selector: {selector} for domain: {domain}")

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        price_element = driver.find_element(By.CSS_SELECTOR, selector)
        logging.info(f"Price element text: {price_element.text}")
        price = (price_element.text.replace('R', '').replace(',', '').strip())
        if '\n' in price:
            price = price.split('\n')[0]
        return float(price)
    except Exception as e:
        logging.error(f"Error finding price / parsing price text on {domain}: {e}")
        return None
    finally:
        driver.quit()


# Background function to monitor price drop
@celery.task(bind=True, max_retries=5, default_retry_delay=300)
def track_price_drop(self, url, email, initial_price=None):
    logging.info(f"Tracking price drop for URL: {url}")
    
    try:
        current_price = check_price(url, selectors)
        if current_price is None:
            raise ValueError(f"Failed to retrieve price for {url}")
    except Exception as e:
        logging.error(f"Error while checking price for {url}: {e}")
        try:
            self.retry(exc=e)  # Retry the task
        except Exception:
            logging.critical(f"Max retries exceeded for {url}. Stopping further attempts.")
        return

    if initial_price is None:
        initial_price = current_price
        logging.info(f"Initial price for {url} set to R{initial_price:.2f}")

    if current_price < initial_price:
        logging.info(f"Price drop detected for {url}: Current Price = R{current_price:.2f}, Initial Price = R{initial_price:.2f}")
        subject = "Price Drop Alert!"
        body = f"The price for your product is now R{current_price:.2f}\n\nCheck it out here:\n{url}"
        send_email(subject, body, email_config['sender_email'], email_config['sender_password'], email)
        logging.info("notification sent")
        return
    else:
        logging.info(f"No price drop detected for {url}. Current Price = R{current_price:.2f}, Initial Price = R{initial_price:.2f}")
        logging.info("Re-scheduling price check in 20 minutes.")
        self.apply_async((url, email, initial_price), countdown=1200)

@app.route('/track', methods=['POST'])
def track_discount():
    try:
        data = request.get_json()
        logging.info(f"Received tracking request: {data.get('url')}")
        url = data.get('url')
        email = data.get('email')

        if not url or not email:
            logging.error("URL or email missing in request")
            return jsonify({"error": "URL and email are required"}), 400
        
        # Adding more websites
        domain = normalize_domain(urlparse(url).netloc)
        if domain not in selectors:
            logging.info(f"Add support for {domain}")
            subject = "Website Support!"
            body = f"Add website support for {domain}"
            send_email(subject, body, email_config['sender_email'], email_config['sender_password'], email_config['support_email'])
            return jsonify({"message": "This website is not supported yet. We are working to add it within 24 hours—please check back soon!"}), 200
        
        # Start price tracking in a background thread
        track_price_drop.delay(url, email)
        logging.info(f"Tracking initiated for {url}")
        return jsonify({"message": "Tracking started. You will be notified when the price drops."}), 200
    except Exception as e:
        logging.error(f"Error in /track endpoint: {e}")
        return jsonify({"error": "An error occurred while processing your request."}), 500
    
# Updates CSS selectors
@app.route('/reload-selectors', methods=['POST'])
def reload_selectors():
    global selectors  
    selectors = load_json('price_selectors.json')
    if not selectors:
        logging.error("Failed to reload selectors.")
        return jsonify({"error": "Failed to reload selectors"}), 500
    logging.info("Selectors reloaded successfully.")
    return jsonify({"message": "Selectors reloaded successfully!"}), 200


# Status route
@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "message": "Service is running",
        "threads": threading.active_count(),
        "selectors_loaded": bool(selectors),
        "email_config_valid": bool(email_config)
    }), 200

# Home route
@app.route('/')
def home():
    return "Price tracker is running!", 200

