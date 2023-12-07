# Logging

## Preparing

Applications relies on the Elite Dangerous systems dataset, which is provided by Gareth Harper.
There's multiple options with various date ranges. You can see all of them here: https://spansh.co.uk/dumps
Note that full dataset has 72.9 GiB of gzipped data.

```bash
wget -O galaxy.json.gz https://downloads.spansh.co.uk/galaxy_1month.json.gz
# OR
wget -O galaxy.json.gz https://downloads.spansh.co.uk/galaxy_7days.json.gz
# OR
wget -O galaxy.json.gz https://downloads.spansh.co.uk/galaxy.json.gz
```
Example of one of the records is stored in example-entry,json.

Also, Elastic requires .emv in root project directory:
```
ELASTIC_PASSWORD=changeme
KIBANA_PASSWORD=changeme
STACK_VERSION=8.11.0
CLUSTER_NAME=docker-cluster
LICENSE=basic
ES_PORT=9200
KIBANA_PORT=5601
ES_MEM_LIMIT=4294967296
KB_MEM_LIMIT=1073741824
LS_MEM_LIMIT=1073741824
ENCRYPTION_KEY=c34d38b3a14956121ff2170e5030b471551370178f43e5626eec58b04a30fae2
```

# Getting the logs

```bash
# for rootful podman
systemctl start podman.socket
export DOCKER_HOST=unix:///run/podman/podman.sock

# if you use rootless podman
systemctl --user start podman.socket
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock

export COMPOSE_PROJECT_NAME=apps
docker-compose --project-directory $PWD -f compose/apps.yml build
# Launch kafka
docker-compose --project-directory $PWD -f compose/apps.yml up -d kafka
# After a while, launch apps that will produce a bunch of logs
docker-compose --project-directory $PWD -f compose/apps.yml up -d storage
docker-compose --project-directory $PWD -f compose/apps.yml up -d statistics
docker-compose --project-directory $PWD -f compose/apps.yml up -d feeder
```


# Vector + Grafana Loki
```bash
export COMPOSE_PROJECT_NAME=loki
docker-compose --project-directory $PWD -f compose/grafana.yml up -d
curl --proto '=https' --tlsv1.2 -sSfL https://sh.vector.dev | bash
~/.vector/bin/vector -c vector.yaml
```
