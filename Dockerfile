FROM python:3.12-slim

# Install system dependencies
# Install system dependencies for lxml, PyQt5, and others
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential python3-dev \
        libxml2-dev libxslt1-dev \
        qtbase5-dev qtwebengine5-dev \
        libqt5webengine5 libqt5webenginewidgets5 \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# 2. Copy requirements file
COPY requirements.txt ./

# 3. Update pip and install dependencies
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r ./requirements.txt

# Copy your app code
COPY . .

EXPOSE 8000

# Set environment variables for connections if needed
ENV DATABASE_URL=/app/index_data.db
ENV REDIS_URL=redis://redis:6379/0

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
