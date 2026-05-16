FROM python:3.11-slim

WORKDIR /app

# Configure pip mirror
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# Install lightweight packages first to reduce memory pressure
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    beautifulsoup4>=4.12.0 \
    pydantic-settings>=2.1.0 \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0 \
    httpx>=0.25.0

# Install elasticsearch separately
RUN pip install --no-cache-dir "elasticsearch[async]>=8.11.0,<9.0.0"

# Install heavy ML packages last (torch, scipy, etc.)
RUN pip install --no-cache-dir \
    sentence-transformers>=2.2.0 \
    faiss-cpu>=1.7.4 \
    openai>=1.6.0

COPY . .

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
