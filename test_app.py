# -*- coding: utf-8 -*-
"""
Flask 웹 애플리케이션의 라우트 및 HTML 연동을 검증하는 실패하는 테스트 파일입니다.
"""

import unittest
from unittest.mock import patch
import app
import logic

class TestAppRoutes(unittest.TestCase):
    """Flask 앱 라우트 연동을 테스트하는 클래스입니다."""

    def setUp(self) -> None:
        """테스트 시작 전 Flask 테스트 클라이언트를 초기화합니다."""
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()

    @patch('scraper.get_post_list')
    @patch('scraper.get_deck_names')
    @patch('logic.analyze_live_data')
    def test_index_route_contains_stylesheet(self, mock_analyze, mock_get_decks, mock_get_posts) -> None:
        """인덱스 페이지 호출 시 아름다운 스타일을 위한 CSS 스타일시트 링크가 포함되어 있는지 검증합니다."""
        # 테스트를 위해 목 데이터를 세팅합니다.
        mock_get_posts.return_value = [{"title": "테스트 포스트", "url": "http://test.url"}]
        mock_get_decks.return_value = ["테스트 덱"]
        mock_analyze.return_value = [{"name": "테스트 카드", "average": "1.0", "variance": "0.0", "std_dev": "0.0", "rounded_average": "1", "delta": "0.0", "adjusted_count": "1", "removability_score": "1.0", "addability_score": "1.0"}]

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # HTML 내용에 styles.css 파일에 대한 링크가 포함되어 있는지 확인합니다.
        # 현재 templates/index.html에는 스타일시트 링크가 없으므로 이 테스트는 실패하게 됩니다.
        html_content = response.data.decode('utf-8')
        self.assertIn('static/css/styles.css', html_content)

if __name__ == '__main__':
    unittest.main()
