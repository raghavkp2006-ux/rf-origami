# RF Origami Design Studio Container
FROM python:3.11-slim

WORKDIR /app

# Zero external pip dependencies required - fully self-contained
COPY . /app

ENV PORT=8080
ENV HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "run_studio.py", "--host", "0.0.0.0", "--no-browser"]
