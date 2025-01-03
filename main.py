from flask import Flask, request, jsonify
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

# enable CORS for the app
CORS(app)

# configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="prcdrop.log"
)

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
        price = price_element.text
        return float(price.replace('R', '').replace(',', '').strip())
    except Exception as e:
        logging.error(f"Error finding price / parsing price text on {domain}: {e}")
        return None
    finally:
        driver.quit()

# Background function to monitor price drop
def track_price_drop(url, email):
    initial_price = check_price(url, selectors)
    if initial_price is None:
        logging.error(f"Failed to retrieve initial price for {url}")
        return

    while True:
        current_price = check_price(url, selectors)
        
        if current_price is None:
            logging.warning(f"Failed to retrieve price for {url}. Retrying in 10 minutes.")
            time.sleep(600)  # Wait before retrying
            continue

        logging.info(f"Current price: R{current_price:.2f}, Initial price: R{initial_price:.2f}")

        if current_price < initial_price:
            logging.info(f"Price dropped for {url}, sending notification.")
            subject = "Price Drop Alert!"
            body = f"The price for your product is now R{current_price:.2f}\n\nCheck it out here:\n{url}"
            send_email(subject, body, email_config['sender_email'], email_config['sender_password'], email)
            break  # Stop tracking once the price drop email is sent

        time.sleep(12000)  # Check every 20 minutes

@app.route('/track', methods=['POST'])
def track_discount():
    data = request.get_json()
    url = data.get('url')
    email = data.get('email')

    if not url or not email:
        logging.error("URL or email missing in request")
        return jsonify({"error": "URL and email are required"}), 400

    # Start price tracking in a background thread
    thread = threading.Thread(target=track_price_drop, args=(url, email))
    thread.start()

    logging.info(f"Tracking initiated for {url}")
    return jsonify({"message": "Tracking started. You will be notified when the price drops."}), 200

# Status route
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "Service is running", "threads": threading.active_count()}), 200

# Home route
@app.route('/')
def home():
    return "Price tracker is running!", 200

if __name__ == "__main__":
    app.run(debug=True)
