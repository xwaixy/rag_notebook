FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g; s|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8001

CMD ["sh", "-c", "uv run python manage.py migrate && uv run python manage.py runserver 0.0.0.0:8001"]
