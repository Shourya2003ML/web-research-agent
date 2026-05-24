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

# ── Temporary debug lines ─────────────────────────────────────────────────────
RUN pip show langgraph
RUN pip show langgraph-checkpoint-sqlite || echo "langgraph-checkpoint-sqlite NOT installed"
RUN python -c "from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver; print('OLD IMPORT WORKS')" || \
    python -c "from langgraph_checkpoint_sqlite import AsyncSqliteSaver; print('NEW IMPORT WORKS')" || \
    echo "NEITHER IMPORT WORKS"
# ── End debug ─────────────────────────────────────────────────────────────────

EXPOSE 7860

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "7860"]
