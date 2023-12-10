# Elasticsearch

## Running

```bash
export COMPOSE_PROJECT_NAME=es
docker-compose -f elastic/compose.yml up -d
```

## Importing logs with Fluent bit

```bash
pytest -s --tb=short -m fluentbit tests/test_elastic.py
```

## Importing logs with Vector

```bash
pytest -s --tb=short -m vector tests/test_elastic.py
```
