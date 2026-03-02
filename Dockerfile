FROM python:3.10-slim

WORKDIR /app

# 安装图片处理基础库
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
