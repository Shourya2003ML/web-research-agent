FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install all dependencies
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend (agent code)
COPY backend/ /backend/

# Copy frontend
COPY frontend/app.py .
COPY frontend/chainlit.md .

RUN mkdir -p /tmp/data
RUN mkdir -p /app/.chainlit

# Add backend to Python path
ENV PYTHONPATH="/backend:$PYTHONPATH"

EXPOSE 7860

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "7860"]
