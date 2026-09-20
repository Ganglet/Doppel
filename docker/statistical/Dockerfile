FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir \
    -r /app/requirements.txt

CMD ["python", "-m", "generators.generate", "--generator", "gaussian_copula", "--seed", "42"]