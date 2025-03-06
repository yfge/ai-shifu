FROM python:3.11 AS base

# ensure /etc/apt/sources.list exists and change APT source to aliyun mirror
RUN if [ -f /etc/apt/sources.list ]; then \
    sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list; \
    sed -i 's|http://security.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; \
    apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*; \
    else \
    echo "No sources.list found!"; \
    fi

# 设置工作目录
WORKDIR /app

# 设置 Poetry 环境变量
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=1.7.1
ENV PATH="/opt/poetry/bin:$PATH"
ENV POETRY_VIRTUALENVS_CREATE=false

# 安装 Poetry
RUN curl -sSL https://install.python-poetry.org | python -

# 复制项目文件并安装依赖
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-interaction --no-ansi

FROM python:3.11-slim
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /opt/poetry /opt/poetry
ENV PATH="/opt/poetry/bin:$PATH"
ENV POETRY_VIRTUALENVS_CREATE=false

# 复制应用代码
COPY app.py app.py
COPY flaskr flaskr
COPY migrations migrations
COPY pyproject.toml poetry.lock* ./

# declare service running on port 5800
EXPOSE 5800

# 使用 Poetry 启动服务
CMD ["poetry", "run", "start"]
