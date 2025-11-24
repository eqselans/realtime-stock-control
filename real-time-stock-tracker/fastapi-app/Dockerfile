FROM python:3.10-slim

WORKDIR /app

# Copy requirements from project tree (build context should be project root)
COPY fastapi-app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and its local dependencies (agents/shared)
COPY fastapi-app/app_fastapi.py ./app_fastapi.py
COPY agents ./agents
COPY tools ./tools

ENV PYTHONPATH=/app

# app entrypoint: module:function -> app_fastapi:app
CMD ["uvicorn", "app_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]