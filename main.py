import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import time

# Setting up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

# Path to ChromeDriver
driver_path = '/home/thabomab/drivers/chromedriver-linux64/chromedriver'
service = Service(executable_path=driver_path)

def load_email_credentials(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# function to send email
def send_email(subject, body, sender_email, sender_password, receiver_email): 
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email  
    msg['Subject'] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        # setting up smtp server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)

        # sending the email
        server.sendmail(sender_email, receiver_email, msg.as_string())  
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending msg: {e}")
    finally:
        server.quit()

# Load price selectors from the JSON file
def load_price_selectors(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def get_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    # Remove 'www.' if it's present in the domain
    if domain.startswith("www."):
        domain = domain[4:]
        
    return domain

def get_price_selector(domain, selectors):
    return selectors.get(domain)

def check_price(url, selectors):
    # Initializes Chrome WebDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)

    # Extracts domain and find corresponding price selector
    domain = get_domain(url)
    price_selector = get_price_selector(domain, selectors)  # Pass both domain and selectors
    print(domain)
    print(price_selector)

    if price_selector is None:
        print(f"No price selector defined for {domain}.")
        driver.quit()
        return None

    try:
        # Waits for the price element to load and scrape it
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, price_selector)))
        price_element = driver.find_element(By.CSS_SELECTOR, price_selector)
        price = price_element.text
        return price
    except Exception as e:
        print(f"Error finding the price on {domain}: {e}")
        return None
    finally:
        driver.quit()  

def monitor_price(url, selectors, email_config, receiver_email):
    initial_price = None
    sender_email = email_config['sender_email']
    sender_password = email_config['sender_password']
    while True:
        price = check_price(url, selectors)

        if price:
            try:
                # Clean and convert price to float
                price_value = float(price.replace('R', '').replace(',', '').strip())  
                
                if initial_price is None:
                    initial_price = price_value
                    print(f"Initial price: R{initial_price}")
                    break 
                else:
                    if price_value < initial_price:
                        print(f"Price dropped! Previous price: R{initial_price}, New price: R{price_value}")
                        subject = "Price Drop Alert!!"
                        body = f"Your item is on Sale!\n\nClick the link to go to the item\n{url}"
                        send_email(subject, body, sender_email, sender_password, receiver_email)
                        # send email notification
                        break
            except ValueError:
                print(f"Error converting the price: {price}")
        else:
            print("Price could not be found or an error occurred.")
        
        # Wait for 5 minutes before checking again
        time.sleep(300)

if __name__ == "__main__":
    url = input("Enter the product URL: ")
    receiver_email = input("Enter email: ")
    selectors = load_price_selectors('price_selectors.json')
    email_config = load_email_credentials('email_config.json')
    monitor_price(url, selectors, email_config, receiver_email)

