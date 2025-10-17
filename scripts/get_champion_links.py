import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

# Setup Chrome options
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# options.add_argument("--headless=new")

# Start the driver
driver = webdriver.Chrome(options=options)
driver.get("https://hellhades.com/raid/tier-list/")

all_links = set()
links_by_page = {}

for page in range(1, 17):  # Pages 1 to 16
    # Wait for pagination tiles to be present
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".tl-pagination-tile"))
    )
    time.sleep(0.25)
    # Extract champion links using JavaScript for better accuracy
    js_script = "Array.from(document.querySelectorAll('a')).filter(a => a.href && a.href.includes('/champions/')).map(a => a.href)"
    links = driver.execute_script(f"return {js_script}")
    links_by_page[str(page)] = sorted(set(links))
    for link in links:
        all_links.add(link)

    # Go to next page if not on the last page
    if page < 16:
        next_page_num = str(page + 1)
        pagination = driver.find_element(
            By.XPATH, f"//div[@class='tl-pagination-tile' and text()='{next_page_num}']"
        )
        driver.execute_script("arguments[0].scrollIntoView();", pagination)
        pagination.click()

# Output all unique champion links
with open("champion_links_by_page.json", "w", encoding="utf-8") as f:
    json.dump(links_by_page, f, indent=2)

driver.quit()
