# Fluent-bit + Elasticsearch

```bash
export COMPOSE_PROJECT_NAME=es
docker-compose -f elastic/compose.yml up -d
pytest -s --tb=short -k fluentbit tests/test_elastic.py 
```
