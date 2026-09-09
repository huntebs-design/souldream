FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

CMD ["sh", "-c", "if [ \"${RAILWAY_SERVICE_NAME:-}\" = \"dilse-web\" ]; then exec uvicorn web:app --host 0.0.0.0 --port=${PORT:-8501}; elif [ \"${PORT:-}\" = \"8501\" ]; then exec streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true --server.baseUrlPath=app; else exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}; fi"]
