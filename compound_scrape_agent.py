from langchain.agents import initialize_agent, AgentType, Tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

# Load environment variables from .env file
load_dotenv()

print("API KEY:", os.getenv("OPENAI_API_KEY"))

# ---------- TOOL FUNCTION (from your scraper) ----------
def scrape_nawy_compounds():
    import time
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.nawy.com/search?category=compound")

        # Wait for the cards-container to be present
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cards-container"))
        )

        # Improved infinite scroll logic for the cards-container
        def scroll_cards_container(min_cards=650, max_total_time=1800, wait_after_scroll=2):
            import time
            start_time = time.time()
            last_count = 0
            while True:
                # Find the parent scrollable div
                scroll_container = driver.find_element(By.CSS_SELECTOR, "div.sc-88b4dfdb-0.cgVQXi")
                # Find the inner container with the cards
                cards_container = scroll_container.find_element(By.CSS_SELECTOR, "div.sc-93b4050e-0.iJSftd")
                cards = cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']")
                if len(cards) >= min_cards:
                    break
                # Scroll the parent container
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scroll_container
                )
                time.sleep(wait_after_scroll)
                new_count = len(cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']"))
                if new_count == last_count or (time.time() - start_time > max_total_time):
                    break
                last_count = new_count

        scroll_cards_container(min_cards=650)
        # Now parse the fully loaded cards-container
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_container = soup.select_one("div.cards-container")
        if not cards_container:
            return json.dumps({"error": "No cards container found on the page"})
        cards = cards_container.select("a[href*='/compound/']")

        if not cards:
            return json.dumps({"error": "No compound listings found in the cards container"})

        compound_data = []
        seen = set()

        for card in cards:
            try:
                href = card.get("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.nawy.com{href}"

                # Area
                area = None
                area_div = card.select_one(".area")
                if area_div:
                    area = area_div.get_text(strip=True)

                # Project Name
                name = None
                name_div = card.select_one(".name")
                if name_div:
                    name = name_div.get_text(strip=True)

                # Description/Summary
                summary = None
                summary_h2 = card.find_next("h2")
                if summary_h2:
                    summary = summary_h2.get_text(strip=True)

                # Property Types
                property_types = [pt.get_text(strip=True) for pt in card.find_all("span", class_="property-type")]

                # Developer Start Price & Resale Start Price
                dev_price = resale_price = None
                card_footer = card.find_next("div", class_="card-footer")
                if card_footer:
                    price_blocks = card_footer.find_all("div", class_="sc-a18c0201-0 HytCg")
                    for block in price_blocks:
                        price_text = block.find("div", class_="price-text")
                        price_value = block.find("span", class_="price")
                        if price_text and price_value:
                            if "Developer Start Price" in price_text.get_text():
                                dev_price = price_value.get_text(strip=True)
                            elif "Resale Start Price" in price_text.get_text():
                                resale_price = price_value.get_text(strip=True)

                # Extract developer name from summary
                developer_name = "N/A"
                if summary:
                    import re
                    match = re.search(r'discover\s+(.*?)\'', summary.lower())
                    if match:
                        developer_name = match.group(1).strip()

                compound_data.append({
                    "Area": area or "N/A",
                    "Project Name": name or "N/A",
                    "Developer Name": developer_name,
                    "Summary": summary or "N/A",
                    "Property Types": property_types,
                    "Developer Start Price": dev_price or "N/A",
                    "Resale Start Price": resale_price or "N/A",
                    "Land Area": "",
                    "Detail Page URL": full_url
                })
            except Exception as e:
                print(f"Error processing card: {e}")
                continue

        if not compound_data:
            return json.dumps({"error": "No valid compound data could be extracted"})

        with open("compounds_west.json", "w", encoding="utf-8") as f:
            json.dump(compound_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(compound_data)} projects and saved to compounds_west.json", "count": len(compound_data)})
    except Exception as e:
        print(f"Error during scraping: {e}")
        return json.dumps({"error": f"Failed to scrape compounds: {str(e)}"})
    finally:
        driver.quit()

# ---------- TOOL WRAPPING ----------
scrape_tool = Tool(
    name="Scrape Nawy Compounds",
    func=lambda _: scrape_nawy_compounds(),
    description="Scrapes compound listings from Nawy and saves them to CSV"
)

# ---------- TOOL FUNCTION (for North areas) ----------
def scrape_nawy_compounds_north():
    import time
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.nawy.com/search?category=compound&areas=12%2C32%2C33%2C34%2C35%2C36%2C37")

        # Wait for the cards-container to be present
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cards-container"))
        )

        def scroll_cards_container(min_cards=650, max_total_time=1800, wait_after_scroll=2):
            import time
            start_time = time.time()
            last_count = 0
            while True:
                scroll_container = driver.find_element(By.CSS_SELECTOR, "div.sc-88b4dfdb-0.cgVQXi")
                cards_container = scroll_container.find_element(By.CSS_SELECTOR, "div.sc-93b4050e-0.iJSftd")
                cards = cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']")
                if len(cards) >= min_cards:
                    break
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scroll_container
                )
                time.sleep(wait_after_scroll)
                new_count = len(cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']"))
                if new_count == last_count or (time.time() - start_time > max_total_time):
                    break
                last_count = new_count

        scroll_cards_container(min_cards=650)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_container = soup.select_one("div.cards-container")
        if not cards_container:
            return json.dumps({"error": "No cards container found on the page"})
        cards = cards_container.select("a[href*='/compound/']")

        if not cards:
            return json.dumps({"error": "No compound listings found in the cards container"})

        compound_data = []
        seen = set()

        for card in cards:
            try:
                href = card.get("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.nawy.com{href}"

                area = None
                area_div = card.select_one(".area")
                if area_div:
                    area = area_div.get_text(strip=True)

                name = None
                name_div = card.select_one(".name")
                if name_div:
                    name = name_div.get_text(strip=True)

                summary = None
                summary_h2 = card.find_next("h2")
                if summary_h2:
                    summary = summary_h2.get_text(strip=True)

                property_types = [pt.get_text(strip=True) for pt in card.find_all("span", class_="property-type")]

                dev_price = resale_price = None
                card_footer = card.find_next("div", class_="card-footer")
                if card_footer:
                    price_blocks = card_footer.find_all("div", class_="sc-a18c0201-0 HytCg")
                    for block in price_blocks:
                        price_text = block.find("div", class_="price-text")
                        price_value = block.find("span", class_="price")
                        if price_text and price_value:
                            if "Developer Start Price" in price_text.get_text():
                                dev_price = price_value.get_text(strip=True)
                            elif "Resale Start Price" in price_text.get_text():
                                resale_price = price_value.get_text(strip=True)

                # Extract developer name from summary
                developer_name = "N/A"
                if summary:
                    import re
                    match = re.search(r'discover\s+(.*?)\'', summary.lower())
                    if match:
                        developer_name = match.group(1).strip()

                compound_data.append({
                    "Area": area or "N/A",
                    "Project Name": name or "N/A",
                    "Developer Name": developer_name,
                    "Summary": summary or "N/A",
                    "Property Types": property_types,
                    "Developer Start Price": dev_price or "N/A",
                    "Resale Start Price": resale_price or "N/A",
                    "Land Area": "",
                    "Detail Page URL": full_url
                })
            except Exception as e:
                continue

        if not compound_data:
            return json.dumps({"error": "No valid compound data could be extracted"})

        with open("compounds_north.json", "w", encoding="utf-8") as f:
            json.dump(compound_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(compound_data)} projects and saved to compounds_north.json", "count": len(compound_data)})
    except Exception as e:
        return json.dumps({"error": f"Failed to scrape compounds: {str(e)}"})
    finally:
        driver.quit()

# ---------- TOOL WRAPPING for North areas ----------
scrape_north_tool = Tool(
    name="Scrape Nawy Compounds North",
    func=lambda _: scrape_nawy_compounds_north(),
    description="Scrapes compound listings from Nawy North areas and saves them to compounds_north.json"
)

# ---------- TOOL FUNCTION (for East areas) ----------
def scrape_nawy_compounds_east():
    import time
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.nawy.com/search?category=compound&areas=2%2C9%2C10%2C16%2C8%2C28%2C41%2C44")

        # Wait for the cards-container to be present
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cards-container"))
        )

        def scroll_cards_container(min_cards=650, max_total_time=1800, wait_after_scroll=2):
            import time
            start_time = time.time()
            last_count = 0
            while True:
                scroll_container = driver.find_element(By.CSS_SELECTOR, "div.sc-88b4dfdb-0.cgVQXi")
                cards_container = scroll_container.find_element(By.CSS_SELECTOR, "div.sc-93b4050e-0.iJSftd")
                cards = cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']")
                if len(cards) >= min_cards:
                    break
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scroll_container
                )
                time.sleep(wait_after_scroll)
                new_count = len(cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']"))
                if new_count == last_count or (time.time() - start_time > max_total_time):
                    break
                last_count = new_count

        scroll_cards_container(min_cards=650)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_container = soup.select_one("div.cards-container")
        if not cards_container:
            return json.dumps({"error": "No cards container found on the page"})
        cards = cards_container.select("a[href*='/compound/']")

        if not cards:
            return json.dumps({"error": "No compound listings found in the cards container"})

        compound_data = []
        seen = set()

        for card in cards:
            try:
                href = card.get("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.nawy.com{href}"

                area = None
                area_div = card.select_one(".area")
                if area_div:
                    area = area_div.get_text(strip=True)

                name = None
                name_div = card.select_one(".name")
                if name_div:
                    name = name_div.get_text(strip=True)

                summary = None
                summary_h2 = card.find_next("h2")
                if summary_h2:
                    summary = summary_h2.get_text(strip=True)

                property_types = [pt.get_text(strip=True) for pt in card.find_all("span", class_="property-type")]

                dev_price = resale_price = None
                card_footer = card.find_next("div", class_="card-footer")
                if card_footer:
                    price_blocks = card_footer.find_all("div", class_="sc-a18c0201-0 HytCg")
                    for block in price_blocks:
                        price_text = block.find("div", class_="price-text")
                        price_value = block.find("span", class_="price")
                        if price_text and price_value:
                            if "Developer Start Price" in price_text.get_text():
                                dev_price = price_value.get_text(strip=True)
                            elif "Resale Start Price" in price_text.get_text():
                                resale_price = price_value.get_text(strip=True)

                # Extract developer name from summary
                developer_name = "N/A"
                if summary:
                    import re
                    match = re.search(r'discover\s+(.*?)\'', summary.lower())
                    if match:
                        developer_name = match.group(1).strip()

                compound_data.append({
                    "Area": area or "N/A",
                    "Project Name": name or "N/A",
                    "Developer Name": developer_name,
                    "Summary": summary or "N/A",
                    "Property Types": property_types,
                    "Developer Start Price": dev_price or "N/A",
                    "Resale Start Price": resale_price or "N/A",
                    "Land Area": "",
                    "Detail Page URL": full_url
                })
            except Exception as e:
                continue

        if not compound_data:
            return json.dumps({"error": "No valid compound data could be extracted"})

        with open("compounds_east.json", "w", encoding="utf-8") as f:
            json.dump(compound_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(compound_data)} projects and saved to compounds_east.json", "count": len(compound_data)})
    except Exception as e:
        return json.dumps({"error": f"Failed to scrape compounds: {str(e)}"})
    finally:
        driver.quit()

# ---------- TOOL WRAPPING for East areas ----------
scrape_east_tool = Tool(
    name="Scrape Nawy Compounds East",
    func=lambda _: scrape_nawy_compounds_east(),
    description="Scrapes compound listings from Nawy East areas and saves them to compounds_east.json"
)

# ---------- TOOL FUNCTION (for West areas) ----------
def scrape_nawy_compounds_west():
    import time
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.nawy.com/search?areas=1%2C26%2C38%2C39%2C40%2C42")

        # Wait for the cards-container to be present
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cards-container"))
        )

        def scroll_cards_container(min_cards=650, max_total_time=1800, wait_after_scroll=2):
            import time
            start_time = time.time()
            last_count = 0
            while True:
                scroll_container = driver.find_element(By.CSS_SELECTOR, "div.sc-88b4dfdb-0.cgVQXi")
                cards_container = scroll_container.find_element(By.CSS_SELECTOR, "div.sc-93b4050e-0.iJSftd")
                cards = cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']")
                if len(cards) >= min_cards:
                    break
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scroll_container
                )
                time.sleep(wait_after_scroll)
                new_count = len(cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/compound/']"))
                if new_count == last_count or (time.time() - start_time > max_total_time):
                    break
                last_count = new_count

        scroll_cards_container(min_cards=650)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_container = soup.select_one("div.cards-container")
        if not cards_container:
            return json.dumps({"error": "No cards container found on the page"})
        cards = cards_container.select("a[href*='/compound/']")

        if not cards:
            return json.dumps({"error": "No compound listings found in the cards container"})

        compound_data = []
        seen = set()

        for card in cards:
            try:
                href = card.get("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.nawy.com{href}"

                area = None
                area_div = card.select_one(".area")
                if area_div:
                    area = area_div.get_text(strip=True)

                name = None
                name_div = card.select_one(".name")
                if name_div:
                    name = name_div.get_text(strip=True)

                summary = None
                summary_h2 = card.find_next("h2")
                if summary_h2:
                    summary = summary_h2.get_text(strip=True)

                property_types = [pt.get_text(strip=True) for pt in card.find_all("span", class_="property-type")]

                dev_price = resale_price = None
                card_footer = card.find_next("div", class_="card-footer")
                if card_footer:
                    price_blocks = card_footer.find_all("div", class_="sc-a18c0201-0 HytCg")
                    for block in price_blocks:
                        price_text = block.find("div", class_="price-text")
                        price_value = block.find("span", class_="price")
                        if price_text and price_value:
                            if "Developer Start Price" in price_text.get_text():
                                dev_price = price_value.get_text(strip=True)
                            elif "Resale Start Price" in price_text.get_text():
                                resale_price = price_value.get_text(strip=True)

                # Extract developer name from summary
                developer_name = "N/A"
                if summary:
                    import re
                    match = re.search(r'discover\s+(.*?)\'', summary.lower())
                    if match:
                        developer_name = match.group(1).strip()

                compound_data.append({
                    "Area": area or "N/A",
                    "Project Name": name or "N/A",
                    "Developer Name": developer_name,
                    "Summary": summary or "N/A",
                    "Property Types": property_types,
                    "Developer Start Price": dev_price or "N/A",
                    "Resale Start Price": resale_price or "N/A",
                    "Land Area": "",
                    "Detail Page URL": full_url
                })
            except Exception as e:
                continue

        if not compound_data:
            return json.dumps({"error": "No valid compound data could be extracted"})

        with open("compounds_west.json", "w", encoding="utf-8") as f:
            json.dump(compound_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(compound_data)} projects and saved to compounds_west.json", "count": len(compound_data)})
    except Exception as e:
        return json.dumps({"error": f"Failed to scrape compounds: {str(e)}"})
    finally:
        driver.quit()

# ---------- TOOL WRAPPING for West areas ----------
scrape_west_tool = Tool(
    name="Scrape Nawy Compounds West",
    func=lambda _: scrape_nawy_compounds_west(),
    description="Scrapes compound listings from Nawy West areas and saves them to compounds_west.json"
)

# ---------- TOOL FUNCTION (for North areas) ----------
def scrape_nawy_properties_north(skip=0):
    import time
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.nawy.com/search?category=property&areas=12%2C32%2C33%2C34%2C35%2C36%2C37")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cards-container"))
        )

        def scroll_cards_container(min_cards=3000, max_total_time=1800, wait_after_scroll=2):
            import time
            start_time = time.time()
            last_count = 0
            while True:
                scroll_container = driver.find_element(By.CSS_SELECTOR, "div.sc-88b4dfdb-0.cgVQXi")
                cards_container = scroll_container.find_element(By.CSS_SELECTOR, "div.sc-93b4050e-0.iJSftd")
                cards = cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/property/']")
                if len(cards) >= min_cards:
                    break
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scroll_container
                )
                time.sleep(wait_after_scroll)
                new_count = len(cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/property/']"))
                if new_count == last_count or (time.time() - start_time > max_total_time):
                    break
                last_count = new_count

        scroll_cards_container(min_cards=3000)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_container = soup.select_one("div.cards-container")
        if not cards_container:
            return json.dumps({"error": "No cards container found on the page"})
        cards = cards_container.select("a[href*='/property/']")
        if skip > 0:
            cards = cards[skip:]

        if not cards:
            return json.dumps({"error": "No property listings found in the cards container"})

        property_data = []
        seen = set()

        for card in cards:
            try:
                href = card.get("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.nawy.com{href}"

                # Area, Property Type, Project Name
                area = card.find_previous("div", class_="area")
                area_text = area.get_text(strip=True) if area else "N/A"
                name_div = card.select_one(".name")
                name_text = name_div.get_text(strip=True) if name_div else "N/A"
                if "," in name_text:
                    property_type, project_name = [x.strip() for x in name_text.split(",", 1)]
                else:
                    property_type, project_name = name_text, "N/A"

                # BUA, Beds, Bathrooms
                bua = beds = baths = "N/A"
                details = card.find_all("div", class_="sc-234f71bd-1 fkOmQT")
                if details and len(details) >= 1:
                    spans = details[0].find_all("div")
                    if len(spans) >= 3:
                        bua = spans[0].get_text(strip=True)
                        beds = spans[1].get_text(strip=True)
                        baths = spans[2].get_text(strip=True)

                # Down Payment
                down_payment = None
                card_footer = card.find_next("div", class_="card-footer")
                if card_footer:
                    dp_container = card_footer.find("div", class_="down-payment-container")
                    if dp_container:
                        down_payment = ' '.join(dp_container.stripped_strings)

                # Price
                price = "N/A"
                price_container = card_footer.find("div", class_="price-container") if card_footer else None
                if price_container:
                    price_span = price_container.find("span", class_="price")
                    if price_span:
                        price = price_span.get_text(separator=" ", strip=True)
                        import re
                        price = re.sub(r"\s*EGP", " EGP", price)
                        price = re.sub(r"\s+", " ", price).strip()

                # Sale Type
                sale_type = "Developer Sale"
                cover_tags = card.find_all("p", class_="tag")
                if cover_tags:
                    for tag in cover_tags:
                        if "resale" in tag.get_text(strip=True).lower():
                            sale_type = "Resale"
                            break

                property_data.append({
                    "Area": area_text,
                    "Property Type": property_type,
                    "Project Name": project_name,
                    "BUA": bua,
                    "Beds": beds,
                    "Bathrooms": baths,
                    "Down Payment": down_payment,
                    "Price": price,
                    "Sale Type": sale_type,
                    "Detail Page URL": full_url
                })
            except Exception as e:
                continue

        if not property_data:
            return json.dumps({"error": "No valid property data could be extracted"})

        with open("property_listings_north.json", "w", encoding="utf-8") as f:
            json.dump(property_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(property_data)} properties and saved to property_listings_north.json", "count": len(property_data)})
    except Exception as e:
        return json.dumps({"error": f"Failed to scrape properties: {str(e)}"})
    finally:
        driver.quit()

# ---------- TOOL WRAPPING for North property listings ----------
scrape_north_property_tool = Tool(
    name="Scrape Nawy Property Listings North",
    func=lambda _: scrape_nawy_properties_north(skip=1632),
    description="Scrapes property listings from Nawy North areas and saves them to property_listings_north.json"
)

# ---------- TOOL FUNCTION (for East property listings) ----------
def scrape_nawy_properties_east(skip=0):
    import time
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.nawy.com/search?category=property&areas=2%2C9%2C10%2C16%2C8%2C28%2C41%2C44")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cards-container"))
        )

        def scroll_cards_container(min_cards=3000, max_total_time=1800, wait_after_scroll=2):
            import time
            start_time = time.time()
            last_count = 0
            while True:
                scroll_container = driver.find_element(By.CSS_SELECTOR, "div.sc-88b4dfdb-0.cgVQXi")
                cards_container = scroll_container.find_element(By.CSS_SELECTOR, "div.sc-93b4050e-0.iJSftd")
                cards = cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/property/']")
                if len(cards) >= min_cards:
                    break
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scroll_container
                )
                time.sleep(wait_after_scroll)
                new_count = len(cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/property/']"))
                if new_count == last_count or (time.time() - start_time > max_total_time):
                    break
                last_count = new_count

        scroll_cards_container(min_cards=3000)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_container = soup.select_one("div.cards-container")
        if not cards_container:
            return json.dumps({"error": "No cards container found on the page"})
        cards = cards_container.select("a[href*='/property/']")
        if skip > 0:
            cards = cards[skip:]

        if not cards:
            return json.dumps({"error": "No property listings found in the cards container"})

        property_data = []
        seen = set()

        for card in cards:
            try:
                href = card.get("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.nawy.com{href}"

                area = card.find_previous("div", class_="area")
                area_text = area.get_text(strip=True) if area else "N/A"
                name_div = card.select_one(".name")
                name_text = name_div.get_text(strip=True) if name_div else "N/A"
                if "," in name_text:
                    property_type, project_name = [x.strip() for x in name_text.split(",", 1)]
                else:
                    property_type, project_name = name_text, "N/A"

                bua = beds = baths = "N/A"
                details = card.find_all("div", class_="sc-234f71bd-1 fkOmQT")
                if details and len(details) >= 1:
                    spans = details[0].find_all("div")
                    if len(spans) >= 3:
                        bua = spans[0].get_text(strip=True)
                        beds = spans[1].get_text(strip=True)
                        baths = spans[2].get_text(strip=True)

                down_payment = None
                card_footer = card.find_next("div", class_="card-footer")
                if card_footer:
                    dp_container = card_footer.find("div", class_="down-payment-container")
                    if dp_container:
                        down_payment = ' '.join(dp_container.stripped_strings)

                price = "N/A"
                price_container = card_footer.find("div", class_="price-container") if card_footer else None
                if price_container:
                    price_span = price_container.find("span", class_="price")
                    if price_span:
                        price = price_span.get_text(separator=" ", strip=True)
                        import re
                        price = re.sub(r"\s*EGP", " EGP", price)
                        price = re.sub(r"\s+", " ", price).strip()

                sale_type = "Developer Sale"
                cover_tags = card.find_all("p", class_="tag")
                if cover_tags:
                    for tag in cover_tags:
                        if "resale" in tag.get_text(strip=True).lower():
                            sale_type = "Resale"
                            break

                property_data.append({
                    "Area": area_text,
                    "Property Type": property_type,
                    "Project Name": project_name,
                    "BUA": bua,
                    "Beds": beds,
                    "Bathrooms": baths,
                    "Down Payment": down_payment,
                    "Price": price,
                    "Sale Type": sale_type,
                    "Detail Page URL": full_url
                })
            except Exception as e:
                continue

        if not property_data:
            return json.dumps({"error": "No valid property data could be extracted"})

        with open("property_listings_east.json", "w", encoding="utf-8") as f:
            json.dump(property_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(property_data)} properties and saved to property_listings_east.json", "count": len(property_data)})
    except Exception as e:
        return json.dumps({"error": f"Failed to scrape properties: {str(e)}"})
    finally:
        driver.quit()

# ---------- TOOL FUNCTION (for East property listings) ----------
scrape_east_property_tool = Tool(
    name="Scrape Nawy Property Listings East",
    func=lambda _: scrape_nawy_properties_east(),
    description="Scrapes property listings from Nawy East areas and saves them to property_listings_east.json"
)

# ---------- TOOL FUNCTION (for West property listings) ----------
def scrape_nawy_properties_west(skip=0):
    import time
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://www.nawy.com/search?category=property&areas=1%2C26%2C38%2C39%2C40%2C42")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cards-container"))
        )

        def scroll_cards_container(min_cards=3000, max_total_time=1800, wait_after_scroll=2):
            import time
            start_time = time.time()
            last_count = 0
            while True:
                scroll_container = driver.find_element(By.CSS_SELECTOR, "div.sc-88b4dfdb-0.cgVQXi")
                cards_container = scroll_container.find_element(By.CSS_SELECTOR, "div.sc-93b4050e-0.iJSftd")
                cards = cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/property/']")
                if len(cards) >= min_cards:
                    break
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scroll_container
                )
                time.sleep(wait_after_scroll)
                new_count = len(cards_container.find_elements(By.CSS_SELECTOR, "a[href*='/property/']"))
                if new_count == last_count or (time.time() - start_time > max_total_time):
                    break
                last_count = new_count

        scroll_cards_container(min_cards=3000)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_container = soup.select_one("div.cards-container")
        if not cards_container:
            return json.dumps({"error": "No cards container found on the page"})
        cards = cards_container.select("a[href*='/property/']")
        if skip > 0:
            cards = cards[skip:]

        if not cards:
            return json.dumps({"error": "No property listings found in the cards container"})

        property_data = []
        seen = set()

        for card in cards:
            try:
                href = card.get("href")
                if not href or href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.nawy.com{href}"

                area = card.find_previous("div", class_="area")
                area_text = area.get_text(strip=True) if area else "N/A"
                name_div = card.select_one(".name")
                name_text = name_div.get_text(strip=True) if name_div else "N/A"
                if "," in name_text:
                    property_type, project_name = [x.strip() for x in name_text.split(",", 1)]
                else:
                    property_type, project_name = name_text, "N/A"

                bua = beds = baths = "N/A"
                details = card.find_all("div", class_="sc-234f71bd-1 fkOmQT")
                if details and len(details) >= 1:
                    spans = details[0].find_all("div")
                    if len(spans) >= 3:
                        bua = spans[0].get_text(strip=True)
                        beds = spans[1].get_text(strip=True)
                        baths = spans[2].get_text(strip=True)

                down_payment = None
                card_footer = card.find_next("div", class_="card-footer")
                if card_footer:
                    dp_container = card_footer.find("div", class_="down-payment-container")
                    if dp_container:
                        down_payment = ' '.join(dp_container.stripped_strings)

                price = "N/A"
                price_container = card_footer.find("div", class_="price-container") if card_footer else None
                if price_container:
                    price_span = price_container.find("span", class_="price")
                    if price_span:
                        price = price_span.get_text(separator=" ", strip=True)
                        import re
                        price = re.sub(r"\s*EGP", " EGP", price)
                        price = re.sub(r"\s+", " ", price).strip()

                sale_type = "Developer Sale"
                cover_tags = card.find_all("p", class_="tag")
                if cover_tags:
                    for tag in cover_tags:
                        if "resale" in tag.get_text(strip=True).lower():
                            sale_type = "Resale"
                            break

                property_data.append({
                    "Area": area_text,
                    "Property Type": property_type,
                    "Project Name": project_name,
                    "BUA": bua,
                    "Beds": beds,
                    "Bathrooms": baths,
                    "Down Payment": down_payment,
                    "Price": price,
                    "Sale Type": sale_type,
                    "Detail Page URL": full_url
                })
            except Exception as e:
                continue

        if not property_data:
            return json.dumps({"error": "No valid property data could be extracted"})

        with open("property_listings_west.json", "w", encoding="utf-8") as f:
            json.dump(property_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(property_data)} properties and saved to property_listings_west.json", "count": len(property_data)})
    except Exception as e:
        return json.dumps({"error": f"Failed to scrape properties: {str(e)}"})
    finally:
        driver.quit()

# ---------- TOOL WRAPPING for West property listings ----------
scrape_west_property_tool = Tool(
    name="Scrape Nawy Property Listings West",
    func=lambda _: scrape_nawy_properties_west(),
    description="Scrapes property listings from Nawy West areas and saves them to property_listings_west.json"
)

# ---------- AGENT SETUP ----------
llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-1106")

agent = initialize_agent(
    tools=[scrape_tool, scrape_north_tool, scrape_east_tool, scrape_west_tool, scrape_north_property_tool, scrape_east_property_tool, scrape_west_property_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=3
)

# ---------- RUN AGENT ----------
if __name__ == "__main__":
    agent.run("Use the Scrape Nawy Property Listings North tool to scrape the remaining north area property listings from Nawy, then use the Scrape Nawy Property Listings East tool to scrape all east area property listings, then use the Scrape Nawy Property Listings West tool to scrape all west area property listings, and save each to their respective files.")
