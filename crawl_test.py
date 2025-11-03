import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By


service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
url = "https://svlabo.jp/blog-entry-1467.html"
driver.get(url)

time.sleep(5)

deck_select_element = driver.find_element(By.ID, "deckname_select_elm")
select_obj = Select(deck_select_element)
select_obj.select_by_index(2)
print("--- [WEB] '필터' 변경: '3번째 덱'('秘術W') 선택 ---")

time.sleep(3)

html = driver.page_source
driver.quit() # 브라우저 종료

soup = BeautifulSoup(html, 'html.parser')

table_head = soup.select_one("#table_header")
all_headers = table_head.find_all("th")
rating_tags = all_headers[6:-4]
rating_int_list = [int(tag.text) if tag.text.strip().isdigit() else 1650 for tag in rating_tags]
print(rating_int_list)

building = soup.select_one("#decklist_body")
all_rows = building.find_all("tr")
print(f"--- [WEB] 크롤링 완료: 총 {len(all_rows)}개의 카드 정보를 찾았습니다. ---")

result_list = []
for row in all_rows:
    card_name_tag = row.find("div")
    if card_name_tag:
        card_name_text = card_name_tag.text

        cells_in_row = row.find_all("td")
        numbers_int_list = [int(cell.text) for cell in cells_in_row[1:-6]]

        average = sum(numbers_int_list) / len(numbers_int_list)
        if average > 2.72:
            result_type = "고정칸"
        elif average < 0.28:
            result_type = "제외칸"
        else:
            result_type = "선택칸"
        result_list.append(f"{card_name_text} -> {result_type} (평균:{average:.2f})")
    else:
        break

for result in result_list:
    print(result)