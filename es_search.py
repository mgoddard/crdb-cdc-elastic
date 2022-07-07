#!/usr/bin/env python3

import sys, os
import requests
import urllib3
import json

# Suppress warnings when using requests with "verify=False" (e.g. no SSL validation)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

es_user = os.getenv("ES_USER", "elastic")
es_url = os.getenv("ES_URL", "https://localhost:9200")
es_index = os.getenv("ES_INDEX", "defaultdb") # CockroachDB database maps to Elastic index
es_passwd = os.getenv("ES_PASSWD") # Must be set

if es_passwd is None:
  print("Environment variable ES_PASSWD must be set")
  sys.exit(1)

if len(sys.argv) < 2:
  print("Usage: {} your query string ...".format(sys.argv[0]))
  sys.exit(1)

q = json.loads("""{ 
  "_source": false,
  "query": {
    "match_phrase": {
      "content": ""
    }
  },
  "highlight": {
    "fields": {
      "content" : { "fragment_size" : 80, "number_of_fragments" : 4 }
    }
  }
}""")
q["query"]["match_phrase"]["content"] = ' '.join(sys.argv[1:])

headers = {"Content-Type": "application/json"}
r = requests.post('/'.join([es_url, es_index, "_search"]), auth=(es_user, es_passwd), verify=False, json=q, headers=headers)
print(json.dumps(r.json(), sort_keys=True, indent=2))

