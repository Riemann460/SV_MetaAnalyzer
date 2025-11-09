from flask import Flask, render_template, jsonify, request

import scraper
import logic

app = Flask(__name__)

@app.route("/")
def index():
    """메인 페이지. 포스트를 가져오고 초기 뷰를 렌더링합니다."""
    try:
        posts = scraper.get_post_list()
        if not posts:
            return "포스트 목록을 가져오지 못했습니다.", 500

        default_post_url = posts[0]['url']
        deck_names = scraper.get_deck_names(default_post_url)
        if not deck_names:
            return "덱 이름을 가져오지 못했습니다.", 500
        
        default_deck_name = deck_names[0]
        initial_data = logic.analyze_live_data(default_post_url, default_deck_name)
        
        if not initial_data:
            return "초기 데이터를 로드하지 못했습니다.", 500
            
        return render_template("index.html", posts=posts, deck_names=deck_names, results=initial_data, selected_post_url=default_post_url, selected_deck=default_deck_name)
    except Exception as e:
        print(f"index 라우트에서 오류 발생: {e}")
        # 프로덕션 환경에서는 더 사용자 친화적인 오류 페이지를 제공하는 것이 좋습니다.
        return "내부 서버 오류가 발생했습니다.", 500

@app.route("/get_deck_analysis")
def get_deck_analysis():
    """특정 덱에 대한 분석 데이터를 가져오는 API 엔드포인트입니다."""
    post_url = request.args.get('url')
    deck_name = request.args.get('deck_name')
    if not post_url or not deck_name:
        return jsonify({"error": "URL과 덱 이름이 필요합니다."}), 400

    try:
        analysis_results = logic.analyze_live_data(post_url, deck_name)
        if not analysis_results:
            return jsonify({"error": "데이터 로딩에 실패했거나 데이터가 없습니다."}), 500
        return jsonify(analysis_results)
    except Exception as e:
        print(f"get_deck_analysis 라우트에서 오류 발생: {e}")
        return jsonify({"error": "내부 서버 오류가 발생했습니다."}), 500

@app.route("/get_deck_names_for_post")
def get_deck_names_for_post():
    """특정 포스트에 대한 덱 이름 목록을 가져오는 API 엔드포인트입니다."""
    post_url = request.args.get('url')
    if not post_url:
        return jsonify({"error": "URL이 필요합니다."}), 400
    
    try:
        deck_names = scraper.get_deck_names(post_url)
        if not deck_names:
            return jsonify({"error": "덱 이름을 가져오지 못했습니다."}), 500
        return jsonify(deck_names)
    except Exception as e:
        print(f"get_deck_names_for_post 라우트에서 오류 발생: {e}")
        return jsonify({"error": "내부 서버 오류가 발생했습니다."}), 500

@app.route("/generate_deck_code", methods=['POST'])
def generate_deck_code():
    """클라이언트로부터 받은 덱 리스트로 덱 코드를 생성합니다."""
    data = request.get_json()
    if not data or 'deck' not in data:
        return jsonify({"error": "덱 데이터가 필요합니다."}), 400

    card_names_list = data['deck']
    class_id = data.get('class_id', 2)
    
    try:
        hashes = logic.generate_deck_hashes(card_names_list)
        deck_code = f"https://shadowverse-wb.com/web/Deck/share?hash=2.{class_id}." + ".".join(hashes) + "&lang=ko"
        return jsonify({"deck_code": deck_code})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"generate_deck_code 라우트에서 오류 발생: {e}")
        return jsonify({"error": "내부 서버 오류가 발생했습니다."}), 500


if __name__ == '__main__':
    # 필수 구성 요소 초기화
    logic.load_card_database()
    scraper.init_driver() # 종료 훅도 함께 등록됩니다
    
    # Flask 앱 실행
    app.run(debug=True)
