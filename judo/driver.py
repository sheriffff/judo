from selenium import webdriver

# to prevent alerts
chrome_options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications": 2}
chrome_options.add_experimental_option("prefs", prefs)
chrome_options.add_argument("--disable-notifications")

driver = webdriver.Chrome('./chromedriver', chrome_options=chrome_options)
driver.maximize_window()
