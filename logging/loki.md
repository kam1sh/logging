# Grafana Loki Stack

## Running

```bash
export COMPOSE_PROJECT_NAME=grafana
docker-compose -f loki/compose.yml up -d
```

## Importing logs with Fluent bit

```bash
pytest -s --tb=short -m fluentbit tests/test_loki.py
```

## Importing logs with Vector

```bash
pytest -s --tb=short -m vector tests/test_loki.py
```
