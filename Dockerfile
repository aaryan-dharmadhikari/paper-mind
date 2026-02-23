FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir nicegui litellm python-dotenv

COPY . .

RUN mkdir -p uploads

EXPOSE 8080

CMD ["python", "main.py"]
