# -*- coding: utf-8 -*-
"""
Cloud Run 배포 테스트를 위한 간단한 'Hello World' Flask 애플리케이션입니다.
"""
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    """'Hello, World!' 메시지를 반환하는 기본 라우트입니다."""
    return 'Hello, World!'

if __name__ == "__main__":
    """
    Gunicorn과 같은 프로덕션 WSGI 서버에서 실행될 때를 대비하여,
    이 스크립트가 직접 실행될 때만 개발 서버를 실행합니다.
    Cloud Run은 Gunicorn을 사용하므로 이 부분은 실행되지 않습니다.
    """
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
