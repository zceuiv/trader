FROM python:3.12-bookworm

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    #libmysqlclient-dev \
    #default-libmysqlclient-dev \
    pkg-config \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装 TA-Lib
RUN wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar -xzf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.6.4-src.tar.gz

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建配置目录
RUN mkdir -p /root/.config/trader /root/.local/share/trader/log

# 设置环境变量
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=dashboard.settings
ENV DJANGO_ALLOW_ASYNC_UNSAFE=true

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 运行命令
CMD ["python", "trader/main.py"] 