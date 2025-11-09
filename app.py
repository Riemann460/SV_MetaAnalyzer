from functools import total_ordering
from datetime import datetime
import time
import math
import json

from flask import Flask, render_template, jsonify, request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import numpy as np

# --- 상수 ---
SVLABO_URL = "https://svlabo.jp/"
DECK_SELECT_ID = "deckname_select_elm"
TABLE_HEADER_ID = "#table_header"
DECKLIST_BODY_ID = "#decklist_body"

import atexit

# --- 전역 변수 ---
driver = None  # Selenium WebDriver 전역 인스턴스
card_database = {} # 카드 이름과 ID를 매핑하는 데이터베이스
card_id_by_normalized_name = {} # 정규화된 카드 이름을 키로 사용하는 DB

app = Flask(__name__)

# 커스텀 문자-이진수 매핑 정의
custom_char_to_binary_map = {}
for i in range(10):
    custom_char_to_binary_map[str(i)] = i
for i in range(26):
    custom_char_to_binary_map[chr(ord('A') + i)] = i + 10
for i in range(26):
    custom_char_to_binary_map[chr(ord('a') + i)] = i + 36
custom_char_to_binary_map['-'] = 62
custom_char_to_binary_map['_'] = 63

# 역 매핑 (정수 -> 문자)
reverse_custom_map = [None] * 64
for char, value in custom_char_to_binary_map.items():
    reverse_custom_map[value] = char

def int_to_custom_base64(value_24bit):
    if not (0 <= value_24bit < (1 << 24)): # 24비트 정수인지 확인
        raise ValueError("입력은 24비트 정수여야 합니다.")

    chars = []
    for i in range(4): # 4개의 문자, 각 6비트
        # 가장 상위 비트부터 6비트씩 추출
        six_bit_value = (value_24bit >> (6 * (3 - i))) & 0x3F # 0x3F는 이진수로 111111
        chars.append(reverse_custom_map[six_bit_value])
    return "".join(chars)

def normalize_card_name(name):
    """카드 이름에서 공백과 같은 불필요한 문자를 제거하여 정규화합니다."""
    return name.replace(" ", "").replace("　", "")

def load_card_database():
    """카드 데이터베이스 JSON 파일을 로드하고, 정규화된 이름의 DB를 생성합니다."""
    global card_database, card_id_by_normalized_name
    try:
        with open("card_database.json", "r", encoding="utf-8") as f:
            card_database = json.load(f)
        
        # 정규화된 이름을 키로, ID를 값으로 하는 새 딕셔너리 생성
        card_id_by_normalized_name = {
            normalize_card_name(name): card_id 
            for name, card_id in card_database.items()
        }
        print(f"성공: {len(card_database)}개의 카드 정보를 로드하고 정규화했습니다.")
    except FileNotFoundError:
        print("경고: card_database.json 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print("경고: card_database.json 파일 파싱에 실패했습니다.")




def shutdown_driver():
    """애플리케이션 종료 시 Selenium 드라이버를 종료합니다."""
    global driver
    if driver:
        print("Shutting down driver...")
        driver.quit()

atexit.register(shutdown_driver)


class Card:
    """각 카드의 통계 및 덱 조정 점수를 저장하는 클래스."""
    def __init__(self, name, weighted_average, variance):
        self.name = name
        self.weighted_average = weighted_average
        self.variance = variance
        self.std_dev = math.sqrt(variance)
        self.rounded_average = int(round(weighted_average, 0))
        self.delta = weighted_average - self.rounded_average
        self.adjusted_count = self.rounded_average
        self.removability_score = 0
        self.addability_score = 0

    def to_dict(self):
        """JSON 응답을 위해 카드 객체를 사전 형태로 변환합니다."""
        return {
            "name": self.name,
            "average": f"{self.weighted_average:.2f}",
            "variance": f"{self.variance:.2f}",
            "std_dev": f"{self.std_dev:.2f}",
            "rounded_average": f"{self.rounded_average}",
            "delta": f"{self.delta:.2f}",
            "adjusted_count": f"{self.adjusted_count}",
            "removability_score": f"{self.removability_score:.4f}" if self.removability_score != np.inf else "INF",
            "addability_score": f"{self.addability_score:.4f}" if self.addability_score != np.inf else "INF"
        }

def init_driver():
    """전역 Selenium WebDriver가 초기화되지 않았을 경우 초기화합니다."""
    global driver
    if driver is None:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_post_list(num_pages=2):
    """메인 페이지에서 여러 페이지에 걸쳐 덱 리스트 비교 포스트 목록을 가져옵니다."""
    init_driver()
    driver.get(SVLABO_URL)
    
    posts = []
    
    for page_num in range(num_pages):
        # 현재 페이지가 완전히 로드될 때까지 기다립니다. (예: 특정 요소 확인)
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
            # '다음 페이지' 버튼이 클릭 가능해질 때까지 기다립니다.
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
    # 덱 선택 후 테이블 헤더가 로드될 때까지 기다립니다.
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, TABLE_HEADER_ID))
    )
    html = driver.page_source
    return BeautifulSoup(html, 'html.parser')

def calculate_initial_analysis(soup):
    """스크랩한 HTML을 분석하여 각 카드의 가중 평균과 분산을 계산합니다."""
    table_head = soup.select_one(TABLE_HEADER_ID)
    if not table_head:
        return []

    # 1. 3단계의 fallback 로직을 사용하여 num_samples와 rating_values를 결정합니다.
    num_samples = 0
    rating_values = []
    header_rows = table_head.find_all("tr")

    if header_rows:
        # 사례 1: 고레이팅 덱 리스트
        rate_header = header_rows[0].find("th", string=lambda t: t and 'レート' in t)
        if rate_header and rate_header.has_attr('colspan'):
            try:
                num_samples = int(rate_header['colspan'])
                if len(header_rows) > 1:
                    rating_headers = header_rows[1].find_all("th")
                    rating_values = [th.text.strip() for th in rating_headers[:-4]]
            except (ValueError, IndexError):
                num_samples = 0

        # 사례 2: 연승 덱 리스트
        if num_samples == 0:
            streak_header = header_rows[0].find("th", string=lambda t: t and '連勝数' in t)
            if streak_header and streak_header.has_attr('colspan'):
                try:
                    num_samples = int(streak_header['colspan'])
                except (ValueError, IndexError):
                    num_samples = 0

        # 사례 3: 일반 포스트(그마 달성 등)
        if num_samples == 0:
            generic_header = header_rows[0].find("th", string=lambda t: t and '採用枚数' in t)
            if generic_header and generic_header.has_attr('colspan'):
                try:
                    num_samples = int(generic_header['colspan'])
                except (ValueError, IndexError):
                    return []

    if num_samples == 0: return []

    # 2. 테이블 본문에서 날짜와 카드 데이터를 추출합니다.
    table_body = soup.select_one(DECKLIST_BODY_ID)
    if not table_body: return []
    all_rows = table_body.find_all("tr")
    date_values = []
    card_rows = []
    for row in all_rows:
        first_cell = row.find(['th', 'td'])
        if not first_cell: continue
        
        if '使用日' in first_cell.text:
            date_values = [cell.text.strip() for cell in row.find_all('td')[:num_samples]]
        elif row.find("div", class_="name_backimg2"):
            card_rows.append(row)

    if not card_rows: return []

    # 3. 통합 가중치 (날짜 & 레이팅)를 계산합니다.
    final_weights = [1.0] * num_samples
    if date_values:
        today = datetime.now()
        half_life_days = 3.0
        for i, date_str in enumerate(date_values):
            if i < len(final_weights):
                try:
                    date_obj = datetime.strptime(date_str, "%m/%d").replace(year=today.year)
                    if date_obj > today: date_obj = date_obj.replace(year=today.year - 1)
                    days_ago = (today - date_obj).days
                    final_weights[i] *= max(0.1, 1.0 - (days_ago / (half_life_days * 2)))
                except ValueError:
                    continue
    if rating_values:
        for i, rating_str in enumerate(rating_values):
            if i < len(final_weights):
                try:
                    rating = int(rating_str)
                    final_weights[i] *= (1.0 + max(0, (rating - 1600) / 100.0 * 0.1))
                except ValueError:
                    continue

    total_weight = sum(final_weights)
    if total_weight == 0: total_weight = 1

    # 4. 각 카드의 데이터를 분석합니다.
    cards = []
    for row in card_rows:
        cells_in_row = row.find_all("td")
        card_name_text = row.find("div", class_="name_backimg2").text.strip()
        
        numbers_str_list = [cell.text for cell in cells_in_row[1:1+num_samples]]
        try:
            numbers_int_list = [int(s) for s in numbers_str_list]
        except ValueError:
            continue

        if len(numbers_int_list) != len(final_weights): continue

        numerator = sum(count * weight for count, weight in zip(numbers_int_list, final_weights))
        
        weighted_average = numerator / total_weight
        weighted_variance = sum(w * ((x - weighted_average) ** 2) for x, w in zip(numbers_int_list, final_weights)) / total_weight
        
        cards.append(Card(card_name_text, weighted_average, weighted_variance))
    return cards

def adjust_deck_count(cards):
    """통계를 분석하여 덱의 총 카드 수를 40장으로 조정합니다.(Weighted Least Squares, Greedy)"""
    v_avg = np.array([card.weighted_average for card in cards])
    v_std_dev = np.array([card.std_dev for card in cards])
    v_current = np.array([card.rounded_average for card in cards])

    cards_to_adjust = sum(v_current) - 40
    epsilon = 1e-6

    while cards_to_adjust != 0:
        best_card_index = -1
        min_penalty = np.inf
        adjustment = -1 if cards_to_adjust > 0 else 1

        for i, card in enumerate(cards):
            if (adjustment == -1 and v_current[i] > 0) or (adjustment == 1 and v_current[i] < 3):
                v_temp = v_current.copy()
                v_temp[i] += adjustment
                v_temp_delta = v_temp - v_avg
                penalty = np.sum(((v_temp_delta / (v_std_dev + epsilon)) ** 2))

                if penalty < min_penalty:
                    min_penalty = penalty
                    best_card_index = i

        if best_card_index != -1:
            v_current[best_card_index] += adjustment
            cards[best_card_index].adjusted_count += adjustment
            cards_to_adjust += adjustment
        else:
            break # 더 이상 조정할 수 없음

def select_replacement_candidates(cards):
    """추천된 표준 덱에 대한 초기 추가/제거 점수를 계산합니다."""
    v_avg = np.array([card.weighted_average for card in cards])
    v_std_dev = np.array([card.std_dev for card in cards])
    v_final = np.array([card.adjusted_count for card in cards])
    epsilon = 1e-6

    for i, card in enumerate(cards):
        if card.adjusted_count > 0:
            v_temp = v_final.copy()
            v_temp[i] -= 1
            penalty = np.sum((((v_temp - v_avg) / (v_std_dev + epsilon)) ** 2))
            card.removability_score = 1 / penalty if penalty != 0 else np.inf

        if card.adjusted_count < 3:
            v_temp = v_final.copy()
            v_temp[i] += 1
            penalty = np.sum((((v_temp - v_avg) / (v_std_dev + epsilon)) ** 2))
            card.addability_score = 1 / penalty if penalty != 0 else np.inf

def analyze_live_data(url, deck_name):
    """주어진 덱에 대한 전체 분석 파이프라인을 조정합니다."""
    soup = scrape_card_data(url, deck_name)
    cards = calculate_initial_analysis(soup)
    if not cards: return []
    
    round_sum = sum(card.rounded_average for card in cards)
    adjust_deck_count(cards)
    select_replacement_candidates(cards)

    analysis_results = [card.to_dict() for card in cards]
    analysis_results.append({
        "name": "총 합", "average": "40", "variance": "N/A", "std_dev": "N/A",
        "rounded_average": f"{round_sum}", "delta": "40", "adjusted_count": "40",
        "removability_score": "N/A", "addability_score": "N/A"
    })
    return analysis_results

@app.route("/")
def index():
    """메인 페이지. 포스트를 가져오고 초기 뷰를 렌더링합니다."""
    posts = get_post_list()
    if not posts:
        return "포스트 목록을 가져오지 못했습니다.", 500

    default_post_url = posts[0]['url']
    deck_names = get_deck_names(default_post_url)
    if not deck_names:
        return "덱 이름을 가져오지 못했습니다.", 500
    
    default_deck_name = deck_names[0]
    initial_data = analyze_live_data(default_post_url, default_deck_name)
    
    if not initial_data:
        return "초기 데이터를 로드하지 못했습니다.", 500
        
    return render_template("index.html", posts=posts, deck_names=deck_names, results=initial_data, selected_post_url=default_post_url, selected_deck=default_deck_name)

@app.route("/get_deck_analysis")
def get_deck_analysis():
    """특정 덱에 대한 분석 데이터를 가져오는 API 엔드포인트."""
    post_url = request.args.get('url')
    deck_name = request.args.get('deck_name')
    if not post_url or not deck_name:
        return jsonify({"error": "URL과 덱 이름이 필요합니다."}), 400

    analysis_results = analyze_live_data(post_url, deck_name)
    if not analysis_results:
        return jsonify({"error": "데이터 로딩에 실패했거나 데이터가 없습니다."}), 500
    return jsonify(analysis_results)

@app.route("/get_deck_names_for_post")
def get_deck_names_for_post():
    """특정 포스트에 대한 덱 이름 목록을 가져오는 API 엔드포인트."""
    post_url = request.args.get('url')
    if not post_url:
        return jsonify({"error": "URL이 필요합니다."}), 400
    
    deck_names = get_deck_names(post_url)
    if not deck_names:
        return jsonify({"error": "덱 이름을 가져오지 못했습니다."}), 500
    return jsonify(deck_names)

@app.route("/generate_deck_code", methods=['POST'])
def generate_deck_code():
    """클라이언트로부터 받은 덱 리스트로 덱 코드를 생성합니다."""
    data = request.get_json()
    if not data or 'deck' not in data:
        return jsonify({"error": "덱 데이터가 필요합니다."}), 400

    card_names_list = data['deck']
    class_id = data.get('class_id', 2) # class_id가 없으면 기본값 2 (Swordcraft) 사용
    
    # 1. 카드 이름별로 매수 카운트
    from collections import Counter
    card_counts = Counter(card_names_list)

    hashes = []
    card_data_for_sorting = [] # (base_card_id, count, encoded_str) 튜플을 저장할 리스트

    # 카드 데이터 수집
    for name in dict.fromkeys(card_names_list):
        count = card_counts[name]
        normalized_name = normalize_card_name(name)
        base_card_id = card_id_by_normalized_name.get(normalized_name)

        if not base_card_id:
            return jsonify({"error": f"'{name}' 카드의 ID를 찾을 수 없습니다."}), 404

        base_card_id = int(base_card_id)
        
        # 커스텀 맵핑을 사용하여 해시 생성
        encoded_str = int_to_custom_base64(base_card_id)
        
        card_data_for_sorting.append((base_card_id, count, encoded_str))
    
    # base_card_id를 기준으로 카드 데이터 정렬
    card_data_for_sorting.sort(key=lambda x: x[0])

    # 정렬된 순서대로 해시 추가
    for base_card_id, count, encoded_str in card_data_for_sorting:
        for _ in range(count):
            hashes.append(encoded_str)
        
    # 최종 덱 코드 생성 (클래스.포맷.해시...)
    deck_code = f"https://shadowverse-wb.com/web/Deck/share?hash=2.{class_id}." + ".".join(hashes) + "&lang=ko"
    
    return jsonify({"deck_code": deck_code})


if __name__ == '__main__':
    load_card_database()
    app.run(debug=True)