FROM python:3.12-slim

WORKDIR /srv

COPY worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /srv/app
COPY worker /srv/worker

CMD ["python", "-m", "worker.runner"]
