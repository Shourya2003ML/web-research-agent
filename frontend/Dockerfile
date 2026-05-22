FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

#Installing dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Copy frontend code
COPY app.py .
COPY chainlit.md .

#Chainlit needs directory to exist
RUN mkdir -p /tmp/data
RUN mkdir -p /app/.chainlit

EXPOSE 8000

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000", "--reload"]