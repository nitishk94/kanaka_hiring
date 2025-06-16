FROM python:3.11-slim AS build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.11-slim AS runner
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY . .

ENV PATH="/opt/venv/bin:$PATH" FLASK_APP=run.py
CMD ["flask","run","--host=0.0.0.0", "--cert=/app/ssl/cert.pem", "--key=/app/ssl/key.pem"]