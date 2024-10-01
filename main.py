from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By  # For locating elements

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

# Specify the path to ChromeDriver
driver_path = '/home/thabomab/drivers/chromedriver-linux64/chromedriver'

# Use Service object to initialize the driver
service = Service(executable_path=driver_path)

# Initialize Chrome WebDriver with options
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open the website
driver.get("https://www.truworths.co.za/skin-scent/product/prod3094269")

# Extract the title and print it
print("Page Title:", driver.title)

# Locate the price element (you need to update the selector based on actual HTML structure)
try:
    # Example: finding the price using its class name, adjust this based on actual HTML.
    price_element = driver.find_element(By.CLASS_NAME, "highlighted-text")  # Replace with the correct class or id
    price = price_element.text
    if (price == "R477"):
        print("Price:", price)
    else:
        print("Price Changed")
except Exception as e:
    print("Error finding the price:", e)

# Close the driver
driver.quit()
