from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# Setting up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

# Path to ChromeDriver
driver_path = '/home/thabomab/drivers/chromedriver-linux64/chromedriver'

# Service object to initialize the driver
service = Service(executable_path=driver_path)

def check_price():
    # Initialize Chrome WebDriver with options
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # Open the website
    driver.get("https://www.truworths.co.za/skin-scent/product/prod3094269")
    time.sleep(10)
    print("Product Name:", driver.title)

    # Locating the price element
    try:
        price_element = driver.find_element(By.CLASS_NAME, "highlighted-text")
        price = price_element.text
        return price
    except Exception as e:
        print("Error finding the price:", e)
        return None
    finally:
        driver.quit()

# Storing initial price
previous_price = check_price()
print(f"Initial price: {previous_price}")

# Checking the price every 10 minutes
while True:
    time.sleep(600)
    current_price = check_price()
    if current_price:
        if current_price == previous_price:
            print("Price remains the same:", current_price)
        else:
            print("Price changed from:", previous_price, "to", current_price)
        previous_price = current_price

