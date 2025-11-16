import math
import json
from datetime import datetime
import numpy as np
from collections import Counter

# logic.py - 데이터 처리 및 비즈니스 로직
import scraper

# --- Constants ---
DECK_SIZE = 40

# --- 전역 변수 대신 사용할 데이터 컨테이너 ---
card_database = {}
card_id_by_normalized_name = {}

# --- Deck Code Utilities ---
custom_char_to_binary_map = {str(i): i for i in range(10)}
custom_char_to_binary_map.update({chr(ord('A') + i): i + 10 for i in range(26)})
custom_char_to_binary_map.update({chr(ord('a') + i): i + 36 for i in range(26)})
custom_char_to_binary_map['-'] = 62
custom_char_to_binary_map['_'] = 63

reverse_custom_map = [None] * 64
for char, value in custom_char_to_binary_map.items():
    reverse_custom_map[value] = char

def int_to_custom_base64(value_24bit):
    if not (0 <= value_24bit < (1 << 24)):
        raise ValueError("입력값은 24비트 정수여야 합니다.")
    chars = []
    for i in range(4):
        six_bit_value = (value_24bit >> (6 * (3 - i))) & 0x3F
        chars.append(reverse_custom_map[six_bit_value])
    return "".join(chars)

def normalize_card_name(name):
    return name.replace(" ", "").replace("　", "")

def load_card_database():
    """카드 데이터베이스를 로드하고 전역 변수를 채웁니다."""
    global card_database, card_id_by_normalized_name
    try:
        with open("card_database.json", "r", encoding="utf-8") as f:
            card_database = json.load(f)
        card_id_by_normalized_name = {
            normalize_card_name(name): card_id
            for name, card_id in card_database.items()
        }
        print(f"성공: {len(card_database)}개의 카드 정보를 로드하고 정규화했습니다.")
    except FileNotFoundError:
        print("경고: card_database.json 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print("경고: card_database.json 파일 파싱에 실패했습니다.")

# --- Data Analysis ---
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

def calculate_initial_analysis(soup):
    table_head = soup.select_one(scraper.TABLE_HEADER_ID)
    if not table_head:
        return []

    num_samples = 0
    rating_values = []
    header_rows = table_head.find_all("tr")

    if header_rows:
        rate_header = header_rows[0].find("th", string=lambda t: t and 'レート' in t)
        if rate_header and rate_header.has_attr('colspan'):
            try:
                num_samples = int(rate_header['colspan'])
                if len(header_rows) > 1:
                    rating_headers = header_rows[1].find_all("th")
                    rating_values = [th.text.strip() for th in rating_headers[:-4]]
            except (ValueError, IndexError):
                num_samples = 0

        if num_samples == 0:
            streak_header = header_rows[0].find("th", string=lambda t: t and '連勝数' in t)
            if streak_header and streak_header.has_attr('colspan'):
                try:
                    num_samples = int(streak_header['colspan'])
                except (ValueError, IndexError):
                    num_samples = 0

        if num_samples == 0:
            generic_header = header_rows[0].find("th", string=lambda t: t and '採用枚数' in t)
            if generic_header and generic_header.has_attr('colspan'):
                try:
                    num_samples = int(generic_header['colspan'])
                except (ValueError, IndexError):
                    return []

    if num_samples == 0: return []

    table_body = soup.select_one(scraper.DECKLIST_BODY_ID)
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
    v_avg = np.array([card.weighted_average for card in cards])
    v_std_dev = np.array([card.std_dev for card in cards])
    v_current = np.array([card.rounded_average for card in cards])

    cards_to_adjust = sum(v_current) - DECK_SIZE
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
            break

def select_replacement_candidates(cards):
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
    soup = scraper.scrape_card_data(url, deck_name)
    cards = calculate_initial_analysis(soup)
    if not cards: return []
    
    round_sum = sum(card.rounded_average for card in cards)
    adjust_deck_count(cards)
    select_replacement_candidates(cards)

    analysis_results = [card.to_dict() for card in cards]
    analysis_results.append({
        "name": "총 합", "average": f"{DECK_SIZE}", "variance": "N/A", "std_dev": "N/A",
        "rounded_average": f"{round_sum}", "delta": f"{DECK_SIZE}", "adjusted_count": f"{DECK_SIZE}",
        "removability_score": "N/A", "addability_score": "N/A"
    })
    return analysis_results

def generate_deck_hashes(card_names_list):
    """주어진 카드 이름 목록에서 덱 코드 해시를 생성합니다."""
    card_counts = Counter(card_names_list)
    hashes = []
    card_data_for_sorting = []

    for name in dict.fromkeys(card_names_list):
        count = card_counts[name]
        normalized_name = normalize_card_name(name)
        base_card_id = card_id_by_normalized_name.get(normalized_name)

        if not base_card_id:
            raise ValueError(f"'{name}' 카드의 ID를 찾을 수 없습니다.")

        base_card_id = int(base_card_id)
        encoded_str = int_to_custom_base64(base_card_id)
        card_data_for_sorting.append((base_card_id, count, encoded_str))
    
    card_data_for_sorting.sort(key=lambda x: x[0])

    for _, count, encoded_str in card_data_for_sorting:
        for _ in range(count):
            hashes.append(encoded_str)
            
    return hashes
