#!/usr/bin/env python
import os
import sys
import requests
import json


def upload(input_file: str,dataset_id: str):
    broker_url = os.environ["_GALAXY_REMOTE_DATA_BROKER_URL"]
    token = os.environ["_GALAXY_OIDC_TOKEN"]
    data = {"input_path": input_file, "token": token, "dataset": dataset_id}
    response = requests.post(broker_url + "/upload", json=data)
    if response.status_code != 200:
        raise requests.HTTPError("wrong response ", response.status_code, response.text)
    res = response.json()
    res["__galaxy_remote_file__"] = 1
    res["remote_broker"] = broker_url
    return res


def __main__():
    input_file = sys.argv[1]
    dataset_id = sys.argv[3]

    try:
        response = upload(input_file,dataset_id)
    except Exception as e:
        print("cannot upload data via remote broker",file=sys.stderr)
        sys.exit(str(e))

    output_file = sys.argv[2]
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(response, indent=4, sort_keys=True))


if __name__ == '__main__':
    __main__()
