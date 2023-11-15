FROM python:3.11 AS build
WORKDIR /app
RUN python3 -m pip install -U pip poetry
COPY . .
RUN poetry build

RUN python -m venv /venv && /venv/bin/pip install dist/*.whl pyuwsgi

FROM python:3.11-slim
WORKDIR /app
COPY --from=build /venv /venv
CMD /venv/bin/uwsgi --http11-socket 0.0.0.0:8000 --master -p 4 --venv /venv -w storage:app
