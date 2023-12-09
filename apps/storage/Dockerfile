FROM python:3.11 AS build
WORKDIR /app
RUN python3 -m pip install -U pip poetry
COPY . .
RUN poetry build

RUN python -m venv /venv && /venv/bin/pip install dist/*.whl gunicorn

FROM python:3.11-slim
WORKDIR /app
COPY --from=build /venv /venv

CMD ["/venv/bin/gunicorn", "-w", "4", \
      "-b", "0.0.0.0:8000", \
      "--access-logfile", "/logs/storage-access.json", \
      "--access-logformat", "{\"remote_ip\":\"%(h)s\",\"request_id\":\"%({X-Request-Id}i)s\",\"response_code\":\"%(s)s\",\"request_method\":\"%(m)s\",\"request_path\":\"%(U)s\",\"request_querystring\":\"%(q)s\",\"request_timetaken\":\"%(D)s\",\"response_length\":\"%(B)s\"}", \
      "storage:app" ]
