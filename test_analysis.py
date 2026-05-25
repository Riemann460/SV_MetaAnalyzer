# -*- coding: utf-8 -*-
"""
카드 정보 추출 및 표준 덱 분석 로직에 대한 실패하는 테스트 코드 파일입니다.
"""

import unittest
from bs4 import BeautifulSoup
import logic

class TestAnalysisLogic(unittest.TestCase):
    """분석 로직에 대한 단위 테스트 클래스입니다."""

    def test_analyze_live_data_empty_html_should_raise_value_error(self) -> None:
        """빈 HTML 또는 유효하지 않은 구조일 때 ValueError 예외가 발생하는지 검증합니다."""
        # 현재 logic.py는 빈 HTML을 받으면 []를 반환하므로, 이 테스트는 실패하게 됩니다.
        invalid_html = "<html><body><div>테이블 없음</div></body></html>"
        soup = BeautifulSoup(invalid_html, "html.parser")
        
        # logic.calculate_initial_analysis 함수를 직접 호출하여 검증합니다.
        with self.assertRaises(ValueError):
            logic.calculate_initial_analysis(soup)

    def test_calculate_initial_analysis_valid_data(self) -> None:
        """유효한 HTML 구조를 분석하여 올바른 카드 통계 객체가 생성되는지 검증합니다."""
        valid_html = """
        <html>
        <body>
            <table>
                <thead id="table_header">
                    <tr>
                        <th colspan="2">レート</th>
                        <th>採用枚数</th>
                    </tr>
                    <tr>
                        <th>1600</th>
                        <th>1700</th>
                    </tr>
                </thead>
                <tbody id="decklist_body">
                    <tr>
                        <td>使用일</td>
                        <td>05/25</td>
                        <td>05/25</td>
                    </tr>
                    <tr>
                        <td><div class="name_backimg2">자연스러운 카드</div></td>
                        <td>3</td>
                        <td>3</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(valid_html, "html.parser")
        cards = logic.calculate_initial_analysis(soup)
        
        self.assertIsNotNone(cards)
        self.assertGreater(len(cards), 0)
        self.assertEqual(cards[0].name, "자연스러운 카드")

    def test_adjust_deck_count_impossible_should_raise_value_error(self) -> None:
        """카드 장수 한계로 인해 덱 매수를 40장으로 조정하는 것이 불가능할 때 ValueError가 발생하는지 검증합니다."""
        # 5개의 카드만 존재할 경우 최대 매수는 15장이므로 40장 조정은 불가능합니다.
        cards = [
            logic.Card(f"카드{i}", 2.0, 0.5) for i in range(5)
        ]
        # 강제로 rounded_average를 설정하여 15장 상태로 만듭니다.
        for card in cards:
            card.rounded_average = 3
            card.adjusted_count = 3
            
        with self.assertRaises(ValueError):
            logic.adjust_deck_count(cards)

    def test_calculate_initial_analysis_jcg_data(self) -> None:
        """JCG 대회 결과 등 '順位' 및 'id=rensho_or_count' 속성을 사용하는 테이블 구조를 정상적으로 파싱하는지 검증합니다."""
        jcg_html = """
        <html>
        <body>
            <table>
                <thead id="table_header">
                    <tr>
                        <th>進化E</th>
                        <th colspan="2" id="rensho_or_count">順位</th>
                        <th>평균</th>
                    </tr>
                    <tr>
                        <th>1</th>
                        <th>2</th>
                    </tr>
                </thead>
                <tbody id="decklist_body">
                    <tr>
                        <td>使用일</td>
                        <td>05/25</td>
                        <td>05/25</td>
                    </tr>
                    <tr>
                        <td><div class="name_backimg2">자연스러운 카드</div></td>
                        <td>3</td>
                        <td>3</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(jcg_html, "html.parser")
        cards = logic.calculate_initial_analysis(soup)
        
        self.assertIsNotNone(cards)
        self.assertGreater(len(cards), 0)
        self.assertEqual(cards[0].name, "자연스러운 카드")

if __name__ == "__main__":
    unittest.main()
