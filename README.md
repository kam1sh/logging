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
