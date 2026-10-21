FROM python:3.13-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .[production]

EXPOSE 8000
CMD ["uvicorn", "hm_recommender.api:app", "--host", "0.0.0.0", "--port", "8000"]

