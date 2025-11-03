from functools import total_ordering

from flask import Flask, render_template
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By

card_data = [
    {
        "name": "刹那のクイックブレイダー",
        "deck_counts": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3, 2],
        "median": 3,
        "average": 2.8,
        "count_3": 11,
        "count_2": 2,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "返還の剣閃",
        "deck_counts": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 3.0,
        "count_3": 13,
        "count_2": 0,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "簒奪のアジト",
        "deck_counts": [2, 2, 3, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3],
        "median": 2,
        "average": 2.3,
        "count_3": 5,
        "count_2": 8,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "異端の侍",
        "deck_counts": [0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "median": 0,
        "average": 0.2,
        "count_3": 0,
        "count_2": 0,
        "count_1": 3,
        "count_0": 10
    },
    {
        "name": "勇猛のルミナスランサー",
        "deck_counts": [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
        "median": 0,
        "average": 0.1,
        "count_3": 0,
        "count_2": 1,
        "count_1": 0,
        "count_0": 12
    },
    {
        "name": "簒奪の肯定者",
        "deck_counts": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 3.0,
        "count_3": 13,
        "count_2": 0,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "簒奪の祈祷者",
        "deck_counts": [3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 2.9,
        "count_3": 12,
        "count_2": 1,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "信念の蹴撃・ランドル",
        "deck_counts": [0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0],
        "median": 0,
        "average": 0.2,
        "count_3": 1,
        "count_2": 0,
        "count_1": 0,
        "count_0": 12
    },
    {
        "name": "干絶の顕現・ギルネリーゼ",
        "deck_counts": [0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "median": 0,
        "average": 0.1,
        "count_3": 0,
        "count_2": 0,
        "count_1": 2,
        "count_0": 11
    },
    {
        "name": "試練の石板",
        "deck_counts": [3, 2, 3, 3, 3, 3, 3, 0, 3, 0, 3, 2, 3],
        "median": 3,
        "average": 2.3,
        "count_3": 9,
        "count_2": 2,
        "count_1": 0,
        "count_0": 2
    },
    {
        "name": "サイレントスナイパー・ワルツ",
        "deck_counts": [3, 2, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 2.8,
        "count_3": 11,
        "count_2": 2,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "常在戦場・カゲミツ",
        "deck_counts": [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "median": 0,
        "average": 0.0,
        "count_3": 0,
        "count_2": 0,
        "count_1": 1,
        "count_0": 12
    },
    {
        "name": "空絶の顕現・オクトリス",
        "deck_counts": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 3.0,
        "count_3": 13,
        "count_2": 0,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "燃え滾る闘志・フェザー",
        "deck_counts": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0],
        "median": 0,
        "average": 0.1,
        "count_3": 0,
        "count_2": 1,
        "count_1": 0,
        "count_0": 12
    },
    {
        "name": "王断の天宮・スタチウム",
        "deck_counts": [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
        "median": 0,
        "average": 0.1,
        "count_3": 0,
        "count_2": 1,
        "count_1": 0,
        "count_0": 12
    },
    {
        "name": "簒奪の団結者",
        "deck_counts": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 3.0,
        "count_3": 13,
        "count_2": 0,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "真紅と群青・ゼタ＆ベアトリクス",
        "deck_counts": [3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 2.9,
        "count_3": 12,
        "count_2": 1,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "卓越のルミナスメイジ",
        "deck_counts": [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
        "median": 0,
        "average": 0.1,
        "count_3": 0,
        "count_2": 1,
        "count_1": 0,
        "count_0": 12
    },
    {
        "name": "レヴィオンの迅雷・アルベール",
        "deck_counts": [3, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 2.9,
        "count_3": 12,
        "count_2": 1,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "リッター・シュナイト",
        "deck_counts": [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "median": 0,
        "average": 0.0,
        "count_3": 0,
        "count_2": 0,
        "count_1": 1,
        "count_0": 12
    },
    {
        "name": "簒奪の継承者・シンセライズ",
        "deck_counts": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        "median": 3,
        "average": 3.0,
        "count_3": 13,
        "count_2": 0,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "運命の黄昏・オーディン",
        "deck_counts": [3, 3, 3, 2, 3, 3, 3, 2, 3, 2, 3, 3, 3],
        "median": 3,
        "average": 2.7,
        "count_3": 10,
        "count_2": 3,
        "count_1": 0,
        "count_0": 0
    },
    {
        "name": "テンタクルバイト",
        "deck_counts": [2, 2, 2, 1, 2, 1, 2, 1, 2, 0, 2, 2, 2],
        "median": 2,
        "average": 1.6,
        "count_3": 0,
        "count_2": 9,
        "count_1": 3,
        "count_0": 1
    }
]

app = Flask(__name__)


def analyze_live_data():
    # 크롤링
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    url = "https://svlabo.jp/blog-entry-1467.html"
    driver.get(url)

    time.sleep(5)

    deck_select_element = driver.find_element(By.ID, "deckname_select_elm")
    select_obj = Select(deck_select_element)
    select_obj.select_by_index(2)

    time.sleep(3)

    html = driver.page_source
    driver.quit()  # 브라우저 종료

    soup = BeautifulSoup(html, 'html.parser')

    table_head = soup.select_one("#table_header")
    all_headers = table_head.find_all("th")
    rating_tags = all_headers[6:-4]
    rating_int_list = [int(tag.text) if tag.text.strip().isdigit() else 1650 for tag in rating_tags]
    weights_list = [(rating-1500)/100 for rating in rating_int_list]
    total_weight = sum(weights_list)

    building = soup.select_one("#decklist_body")
    all_rows = building.find_all("tr")
    print(f"--- [WEB] 크롤링 완료: 총 {len(all_rows)}개의 카드 정보를 찾았습니다. ---")

    # 결과 출력
    analysis_results = []
    for row in all_rows:
        card_name_tag = row.find("div")
        if card_name_tag:
            card_name_text = card_name_tag.text

            cells_in_row = row.find_all("td")
            numbers_int_list = [int(cell.text) for cell in cells_in_row[1:-6]]

            numerator = sum(count * weight for count, weight in zip(numbers_int_list, weights_list))
            weighted_average = numerator / total_weight
            if weighted_average > 2.72:
                result_type = "고정칸"
            elif weighted_average < 0.28:
                result_type = "제외칸"
            else:
                result_type = "선택칸"

            analysis_results.append({
                "name": card_name_text,
                "type": result_type,
                "average": f"{weighted_average:.2f}"
            })
        else:
            break

    return analysis_results

@app.route("/")
def hello_world():
    live_data = analyze_live_data()
    if not live_data:
        return "데이터 로딩에 실패했거나 데이터가 없습니다."
    return render_template("index.html", results=live_data)


if __name__ == '__main__':
    app.run(debug=True)