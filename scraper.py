# scraper.py - 데이터 수집 (웹 스크래핑)
import atexit
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- 상수 ---
SVLABO_URL = "https://svlabo.jp/"
DECK_SELECT_ID = "deckname_select_elm"
TABLE_HEADER_ID = "#table_header"
DECKLIST_BODY_ID = "#decklist_body"

# --- 전역 WebDriver 인스턴스 ---
driver = None

def init_driver():
    """전역 Selenium WebDriver가 초기화되지 않았을 경우 초기화합니다."""
    global driver
    if driver is None:
        print("새로운 Chrome 드라이버를 초기화합니다...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        # 드라이버가 초기화될 때만 종료 훅을 등록합니다.
        atexit.register(shutdown_driver)

def shutdown_driver():
    """Selenium WebDriver를 종료합니다."""
    global driver
    if driver:
        print("드라이버를 종료합니다...")
        driver.quit()
        driver = None

def get_post_list(num_pages=2):
    """메인 사이트의 여러 페이지에 걸쳐 덱 리스트 비교 포스트 목록을 가져옵니다."""
    init_driver()
    driver.get(SVLABO_URL)
    
    posts = []
    
    for page_num in range(num_pages):
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            try:
                title = link.text
                if "デッキリスト比較" in title:
                    url = link.get_attribute('href')
                    if url and url not in [p['url'] for p in posts]:
                        posts.append({"title": title, "url": url})
            except Exception:
                continue
        
        try:
            next_page_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.pager_next_link"))
            )
            driver.execute_script("arguments[0].click();", next_page_link)
        except Exception as e:
            print(f"다음 페이지를 찾을 수 없어 {page_num + 1}페이지에서 중단합니다: {e}")
            break
            
    return posts

def get_deck_names(url):
    """주어진 포스트 URL에 대해 사용 가능한 덱 타입 목록을 가져옵니다."""
    init_driver()
    driver.get(url)
    deck_select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, DECK_SELECT_ID))
    )
    select_obj = Select(deck_select_element)
    options = [option.text for option in select_obj.options]
    return options

def scrape_card_data(url, deck_name):
    """포스트 페이지에서 특정 덱 타입을 선택하고, 파싱된 HTML(BeautifulSoup 객체)을 반환합니다."""
    init_driver()
    driver.get(url)
    deck_select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, DECK_SELECT_ID))
    )
    select_obj = Select(deck_select_element)
    select_obj.select_by_visible_text(deck_name)
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, TABLE_HEADER_ID))
    )
    html = driver.page_source
    return BeautifulSoup(html, 'html.parser')
