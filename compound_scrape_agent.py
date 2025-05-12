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

                compound_data.append({
                    "Area": area or "N/A",
                    "Project Name": name or "N/A",
                    "Summary": summary or "N/A",
                    "Property Types": property_types,
                    "Developer Start Price": dev_price or "N/A",
                    "Resale Start Price": resale_price or "N/A",
                    "Detail Page URL": full_url
                })
            except Exception as e:
                print(f"Error processing card: {e}")
                continue

        if not compound_data:
            return json.dumps({"error": "No valid compound data could be extracted"})

        with open("nawy_compound_listings.json", "w", encoding="utf-8") as f:
            json.dump(compound_data, f, ensure_ascii=False, indent=2)
        return json.dumps({"message": f"Extracted {len(compound_data)} projects and saved to nawy_compound_listings.json", "count": len(compound_data)})
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

# ---------- AGENT SETUP ----------
llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-1106")

agent = initialize_agent(
    tools=[scrape_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=3
)

# ---------- RUN AGENT ----------
if __name__ == "__main__":
    agent.run("Scrape all compound listings from Nawy and save to a file")
