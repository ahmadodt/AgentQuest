FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip \
    && pip install . \
    && pip install llama-cpp-python

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py"]
