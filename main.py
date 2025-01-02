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
import time
from urllib.parse import urlparse
import threading
import logging

app = Flask(__name__)

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

driver_path = '/home/thabomab/drivers/chromedriver-linux64/old_chromedriver'

# Utility function to load JSON data
def load_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading Json File {file_path}: {e}")

selectors = load_json('price_selectors.json')
email_config = load_json('email_config.json')

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
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(driver_path), options=chrome_options)
    driver.get(url)

    domain = urlparse(url).netloc
    selector = selectors.get(domain)
    
    if not selector:
        logging.error(f"No selector found for {domain}")
        driver.quit()
        return None
    
    logging.info(f"using selector: {selector} for domain: {domain}")

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        price_element = driver.find_element(By.CSS_SELECTOR, selector)
        price = price_element.text
        return float(price.replace('R', '').replace(',', '').strip())
    except Exception as e:
        logging.error(f"Error finding price / parsing price text on {domain}: {e}")
        return None
    finally:
        driver.quit()

# Background function to monitor price drop
def track_price_drop(url, email, initial_price):
    while True:
        current_price = check_price(url, selectors)
        
        if current_price is None:
            logging.warning(f"Failed to retrieve price for {url}. retrying in 5 min.")
            time.sleep(300)  # Waits before retrying
            continue

        logging.info(f"Current price: R{current_price:.2f}, Initial price: R{initial_price}")

        if current_price < initial_price:
            logging.info(f"Price dropped for {url} sending notification.")
            subject = "Price Drop Alert!"
            body = f"The price for your product is now R{current_price:.2f}\nCheck it out here: {url}"
            send_email(subject, body, email_config['sender_email'], email_config['sender_password'], email)
            break  # Stops tracking once the price drop email is sent

        time.sleep(300)  # Checks every 5 minutes

@app.route('/track', methods=['POST'])
def track_discount():
    data = request.get_json()
    url = data.get('url')
    email = data.get('email')

    if not url or not email:
        logging.error("Url or email missing in request")
        return jsonify({"error": "URL and email are required"}), 400

    initial_price = check_price(url, selectors)
    if initial_price is None:
        logging.error(f"failed to retrieve initial price for {url}")
        return jsonify({"error": "Failed to retrieve price"}), 500

    # Starts the price tracking in a background thread
    thread = threading.Thread(target=track_price_drop, args=(url, email, initial_price))
    thread.start()

    logging.info(f"Tracking price for {url}")
    return jsonify({"message": "Tracking started. You will be notified if the price drops."}), 200

# status route
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "Service is running", "threads": threading.active_count()}), 200

# home route
@app.route('/')
def home():
    return "Price tracker is running!", 200


if __name__ == "__main__":
    app.run(debug=True)
