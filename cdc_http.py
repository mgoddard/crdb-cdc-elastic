#!/usr/bin/env python3

"""

SET CLUSTER SETTING kv.rangefeed.enabled = true;

CREATE CHANGEFEED FOR TABLE my_table
INTO 'http://localhost:3000/'
WITH updated, full_table_name;

Ref.

  https://www.cockroachlabs.com/docs/stable/create-changefeed.html
  https://www.elastic.co/guide/en/elasticsearch/reference/current/targz.html
  https://medium.com/tech-explained/getting-hands-on-with-elasticsearch-9969a2894f8a
  https://www.elastic.co/guide/en/elasticsearch/guide/master/denormalization.html

"""

import os, json, re, sys, logging
from flask import (Flask, request, jsonify)
import requests
import urllib3
import urllib.parse

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")

# Suppress warnings when using requests with "verify=False" (e.g. no SSL validation)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
port = int(os.getenv("PORT", 3000))

es_user = os.getenv("ES_USER", "elastic")
es_passwd = os.getenv("ES_PASSWD", "")
es_url = os.getenv("ES_URL", "https://localhost:9200")

# Command line methods
# TODO: Add a --query mode
if len(sys.argv) > 1:
  if "--create-index" == sys.argv[1]:
    index_name = sys.argv[2]
    r = requests.put(es_url + "/" + index_name, auth=(es_user, es_passwd), verify=False)
    if 401 == r.status_code:
      logging.error("Unauthorized: ensure your ES_USER and ES_PASSWD environment variables are set")
      sys.exit(1)
    elif 200 != r.status_code:
      logging.error(json.dumps(r.json(), sort_keys=True, indent=2))
      sys.exit(1)
    else:
      sys.exit(0)
  else:
    logging.warn("Usage: {} --create-index index_name".format(sys.argv[0]))
    sys.exit(1)

@app.route("/<date>/<full_id>", methods = ["PUT"])
def jsonHandler(date, full_id):
  logging.debug("date: {}, full_id: {}".format(date, full_id))
  db = None
  schema = None
  table = None
  m = re.search(r'^.+?-(\w+)\.(\w+)\.(\w+)-\d+\.ndjson', full_id)
  if m is not None:
    db = m.group(1)
    schema = m.group(2)
    table = m.group(3)
    logging.debug("DB: {}, schema: {}, table: {}".format(db, schema, table))
    index_name = db
    type_name = schema + '-' + table
    # Could be a multi-row TXN
    for line in request.data.decode().strip().split('\n'):
      obj = json.loads(line)
      es_id = type_name + '-' + '-'.join([x.replace('-', '') for x in obj["key"]])
      es_id = urllib.parse.quote_plus(es_id) # ES doesn't like '/' in the ID
      es_json = obj["after"]
      es_path = '/'.join([index_name, "_doc", es_id])
      if es_json is None:
        # This corresponds to a DELETE in Elastic
        r = requests.delete(es_url + '/' + es_path, auth=(es_user, es_passwd), verify=False)
        logging.info("ES status code: {}".format(r.status_code))
      else:
        headers = {"Content-Type": "application/json"}
        r = requests.post(es_url + '/' + es_path, auth=(es_user, es_passwd), verify=False, json=es_json, headers=headers)
        logging.info("ES status code: {}".format(r.status_code))
      logging.info("ES response: %s", r.json())
  return "OK", 200

@app.route("/status", methods = ["GET"])
def status():
  return "OK", 200

if __name__ == "__main__":
  from waitress import serve
  serve(app, host="127.0.0.1", port=port)

