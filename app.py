from functools import total_ordering

from flask import Flask, render_template, jsonify, request
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import numpy as np
import math

driver = None # Selenium 웹 드라이버를 위한 전역 변수

app = Flask(__name__)


class Card:
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

def select_replacement_candidates(cards):
    v_avg = np.array([card.weighted_average for card in cards])
    v_std_dev = np.array([card.std_dev for card in cards])
    v_final = np.array([card.adjusted_count for card in cards])
    epsilon = 1e-6

    # 제거 가능성 점수 계산
    for i, card in enumerate(cards):
        if card.adjusted_count > 0:
            v_temp = v_final.copy()
            v_temp[i] -= 1
            v_temp_delta = v_temp - v_avg
            penalty = np.sum(((v_temp_delta / (v_std_dev + epsilon)) ** 2))
            card.removability_score = 1 / penalty if penalty != 0 else np.inf

    # 추가 가능성 점수 계산
    for i, card in enumerate(cards):
        if card.adjusted_count < 3:
            v_temp = v_final.copy()
            v_temp[i] += 1
            v_temp_delta = v_temp - v_avg
            penalty = np.sum(((v_temp_delta / (v_std_dev + epsilon)) ** 2))
            card.addability_score = 1 / penalty if penalty != 0 else np.inf


def init_driver():
    global driver
    if driver is None:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)

def get_post_list():
    init_driver()
    url = "https://svlabo.jp/"
    driver.get(url)
    time.sleep(5)  # 동적 페이지 로딩 대기

    posts = []
    all_links = driver.find_elements(By.TAG_NAME, "a")
    
    for link in all_links:
        try:
            title = link.text
            # "デッキリスト比較"가 포함된 포스트만 필터링
            if "デッキリスト比較" in title:
                url = link.get_attribute('href')
                # 중복 방지를 위해 URL 존재 여부 및 중복 체크
                if url and url not in [p['url'] for p in posts]:
                    posts.append({"title": title, "url": url})
        except Exception as e:
            # Stale-Element-Exception 등 반복 중 발생 가능한 오류 처리
            continue
    return posts

def get_deck_names(url):
    init_driver()
    driver.get(url)
    time.sleep(5)  # 동적 페이지 로딩 대기
    deck_select_element = driver.find_element(By.ID, "deckname_select_elm")
    select_obj = Select(deck_select_element)
    options = [option.text for option in select_obj.options]
    return options

def scrape_card_data(url, deck_name):
    init_driver()
    driver.get(url)
    time.sleep(5)  # 동적 페이지 로딩 대기
    deck_select_element = driver.find_element(By.ID, "deckname_select_elm")
    select_obj = Select(deck_select_element)
    select_obj.select_by_visible_text(deck_name)
    time.sleep(3)  # 데이터 업데이트 대기
    html = driver.page_source
    return BeautifulSoup(html, 'html.parser')

def calculate_initial_analysis(soup):
    table_head = soup.select_one("#table_header")
    all_headers = table_head.find_all("th")
    rating_tags = all_headers[6:-4]
    rating_int_list = [int(tag.text) if tag.text.strip().isdigit() else 1650 for tag in rating_tags]
    weights_list = [(rating - 1600) / 100 for rating in rating_int_list]
    total_weight = sum(weights_list)

    building = soup.select_one("#decklist_body")
    all_rows = building.find_all("tr")
    print(f"--- [WEB] 크롤링 완료: 총 {len(all_rows)}개의 카드 정보를 찾았습니다. ---")

    cards = []
    for row in all_rows:
        card_name_tag = row.find("div")
        if not card_name_tag:
            break
        card_name_text = card_name_tag.text
        cells_in_row = row.find_all("td")
        numbers_int_list = [int(cell.text) for cell in cells_in_row[1:-6]]
        numerator = sum(count * weight for count, weight in zip(numbers_int_list, weights_list))
        
        # 가중치 합계가 0일 경우의 'divide by zero' 오류 방지
        if total_weight == 0:
            weighted_average = 0.0
            weighted_variance = 0.0
        else:
            weighted_average = numerator / total_weight
            weighted_variance = sum(w * ((x - weighted_average) ** 2) for x, w in zip(numbers_int_list, weights_list)) / total_weight
        
        cards.append(Card(card_name_text, weighted_average, weighted_variance))
    return cards

# 덱의 총 카드 수가 40장이 되도록 카드를 추가/제거하여 "표준 덱"을 구성합니다.
# 전체 카드 분포와의 편차(패널티)가 가장 적어지는 카드를 순차적으로 찾아 조정합니다.
def adjust_deck_count(cards):
    v_avg = np.array([card.weighted_average for card in cards])
    v_std_dev = np.array([card.std_dev for card in cards])
    v_current = np.array([card.rounded_average for card in cards])

    cards_to_adjust = sum(v_current) - 40
    epsilon = 1e-6  # 0으로 나누기 오류 방지

    while cards_to_adjust != 0:
        best_card_index = -1
        min_penalty = np.inf

        # 추가할지 제거할지 결정
        adjustment = -1 if cards_to_adjust > 0 else 1

        # 가장 패널티가 적은 카드를 찾기
        for i, card in enumerate(cards):
            if (adjustment == -1 and v_current[i] > 0) or (adjustment == 1 and v_current[i] < 3):
                v_temp = v_current.copy()
                v_temp[i] += adjustment
                
                v_temp_delta = v_temp - v_avg
                
                penalty = np.sum(((v_temp_delta / (v_std_dev + epsilon)) ** 2))

                if penalty < min_penalty:
                    min_penalty = penalty
                    best_card_index = i

        # 찾은 최적의 카드를 덱에 반영
        if best_card_index != -1:
            v_current[best_card_index] += adjustment
            cards[best_card_index].adjusted_count += adjustment
            cards_to_adjust += adjustment
        else:
            # 더 이상 조정할 카드가 없으면 루프 종료
            break

def select_replacement_candidates(cards):
    v_avg = np.array([card.weighted_average for card in cards])
    v_std_dev = np.array([card.std_dev for card in cards])
    v_final = np.array([card.adjusted_count for card in cards])
    epsilon = 1e-6

    # 제거 가능성 점수 계산
    for i, card in enumerate(cards):
        if card.adjusted_count > 0:
            v_temp = v_final.copy()
            v_temp[i] -= 1
            v_temp_delta = v_temp - v_avg
            penalty = np.sum(((v_temp_delta / (v_std_dev + epsilon)) ** 2))
            card.removability_score = 1 / penalty

    # 추가 가능성 점수 계산
    for i, card in enumerate(cards):
        if card.adjusted_count < 3:
            v_temp = v_final.copy()
            v_temp[i] += 1
            v_temp_delta = v_temp - v_avg
            penalty = np.sum(((v_temp_delta / (v_std_dev + epsilon)) ** 2))
            card.addability_score = 1 / penalty

def analyze_live_data(url, deck_name):
    soup = scrape_card_data(url, deck_name)
    cards = calculate_initial_analysis(soup)
    round_sum = sum(card.rounded_average for card in cards)
    adjust_deck_count(cards)
    select_replacement_candidates(cards)

    analysis_results = [card.to_dict() for card in cards]
    analysis_results.append({
        "name": "총 합",
        "average": "40",
        "variance": "N/A",
        "std_dev": "N/A",
        "rounded_average": f"{round_sum}",
        "delta": "40",
        "adjusted_count": "40",
        "removability_score": "N/A",
        "addability_score": "N/A"
    })
    return analysis_results

@app.route("/")
def index():
    posts = get_post_list()
    if not posts:
        return "포스트 목록을 가져오지 못했습니다.", 500

    # 기본값으로 첫 포스트의 첫 덱 데이터를 로드
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
    post_url = request.args.get('url')
    if not post_url:
        return jsonify({"error": "URL이 필요합니다."}), 400
    
    deck_names = get_deck_names(post_url)
    if not deck_names:
        return jsonify({"error": "덱 이름을 가져오지 못했습니다."}), 500
    return jsonify(deck_names)


if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        if driver:
            print("Shutting down driver...")
            driver.quit()