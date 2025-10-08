FROM python:3.11

# install Python packages
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 安裝中文字體
RUN apt update && \
    apt install -y fonts-noto-cjk && \
    apt clean && rm -rf /var/lib/apt/lists/*
