FROM python:3.11-slim

WORKDIR /app

# 系統相依（若需編譯可加上 build-essential）
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 專案程式碼掛載用 volume，這裡只複製 manage.py 讓容器可啟動
COPY app /app

# 啟動前檢查/建立 text index
CMD python manage.py ensure_text_index && \
    python manage.py runserver 0.0.0.0:8000