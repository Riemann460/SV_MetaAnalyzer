# 1. 베이스 이미지 설정 (Python 3.9 슬림 버전)
FROM python:3.9-slim

# 2. Chrome 및 Chromedriver 설치에 필요한 패키지 및 의존성 설치
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    curl \
    # Chrome dependencies
    libxss1 \
    libappindicator1 \
    libindicator7 \
    fonts-liberation \
    xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 3. Google Chrome 공식 저장소 및 서명 키 추가
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /etc/apt/trusted.gpg.d/google-chrome.gpg && \
    echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# 4. Google Chrome Stable 설치
RUN apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 5. 호환되는 Chromedriver 설치
RUN CHROME_VERSION=$(google-chrome --product-version | grep -o "^[0-9]*") && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget -q --continue -P /tmp "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver_linux64.zip && \
    chmod +x /usr/local/bin/chromedriver

# 6. Python 의존성 파일 복사 및 설치
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. 전체 소스 코드 복사
COPY . .

# 8. 컨테이너가 리슨할 포트 설정
EXPOSE 8080

# 9. 애플리케이션 실행
# Cloud Run은 PORT 환경 변수를 자동으로 주입합니다.
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
