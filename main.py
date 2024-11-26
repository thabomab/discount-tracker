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

app = Flask(__name__)

# Set up Chrome options for Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

driver_path = '/home/thabomab/drivers/chromedriver-linux64/chromedriver'

# Utility function to load JSON data
def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

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
        print(f"Error sending email: {e}")

# Price tracking function
def check_price(url, selectors):
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(driver_path), options=chrome_options)
    driver.get(url)

    domain = urlparse(url).netloc
    selector = selectors.get(domain)
    
    if not selector:
        driver.quit()
        return None

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        price_element = driver.find_element(By.CSS_SELECTOR, selector)
        price = price_element.text
        return float(price.replace('R', '').replace(',', '').strip())
    except Exception as e:
        print(f"Error finding price on {domain}: {e}")
        return None
    finally:
        driver.quit()

# Background function to monitor price drop
def track_price_drop(url, email, initial_price):
    while True:
        current_price = check_price(url, selectors)
        
        if current_price is None:
            print("Failed to retrieve price.")
            time.sleep(300)  # Wait before retrying
            continue

        print(f"Current price: R{current_price}, Initial price: R{initial_price}")

        if current_price < initial_price:
            print("Price dropped!")
            subject = "Price Drop Alert!"
            body = f"The price for your product has dropped!\n\nNew price: R{current_price}\nCheck it out here: {url}"
            send_email(subject, body, email_config['sender_email'], email_config['sender_password'], email)
            break  # Stop tracking once the price drop email is sent

        time.sleep(300)  # Check every 5 minutes

@app.route('/track', methods=['POST'])
def track_discount():
    data = request.get_json()
    url = data.get('url')
    email = data.get('email')

    if not url or not email:
        return jsonify({"error": "URL and email are required"}), 400

    initial_price = check_price(url, selectors)
    if initial_price is None:
        return jsonify({"error": "Failed to retrieve price"}), 500

    # Start the price tracking in a background thread
    thread = threading.Thread(target=track_price_drop, args=(url, email, initial_price))
    thread.start()

    return jsonify({"message": "Tracking started. You will be notified if the price drops."}), 200

if __name__ == "__main__":
    app.run(debug=True)
