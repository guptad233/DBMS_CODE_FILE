from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# Path to ChromeDriver
chrome_driver_path = r"C:/Users/aarus/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"

options = Options()
options.add_argument("--start-maximized")

service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

# Open Login Page
driver.get("https://cloud-project-lydg.onrender.com/login/")
time.sleep(3)

# Enter Login Credentials
username_field = driver.find_element(By.NAME, "username")
password_field = driver.find_element(By.NAME, "password")

username_field.send_keys("singlaaarush9@gmail.com")
password_field.send_keys("JAISHREERAM123")

time.sleep(1)

# Click Login Button
login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
login_button.click()
time.sleep(4)

# Verify successful login using Dashboard text
if "Dashboard" in driver.page_source:
    print("🎉 Login Test Passed - Dashboard Visible")
else:
    print("❌ Login Test Failed")

driver.quit()
