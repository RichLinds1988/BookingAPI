FROM python:3.12-slim as builder

WORKDIR /project

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m venv "$VIRTUAL_ENV"

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt


FROM python:3.12-slim

WORKDIR /project

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends make && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /opt/venv /opt/venv

COPY . .

EXPOSE 8000

CMD ["bash", "-c", "alembic -c migrations/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir src"]