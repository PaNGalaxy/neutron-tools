#!/usr/bin/env python
import os
import sys
import requests
import json


def download(remote_id: str,output_file: str):
    broker_url = os.environ["_GALAXY_REMOTE_DATA_BROKER_URL"]
    token = os.environ["_GALAXY_OIDC_TOKEN"]
    data = {"uid": remote_id, "token": token, "output_path": output_file}
    response = requests.post(broker_url + "/download", json=data)
    if response.status_code != 200:
        raise requests.HTTPError("wrong response ", response.status_code, response.text)

def __main__():
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, 'r',encoding="utf-8") as f:
        data = json.load(f)

    remote_id= data["uid"]

    try:
        download(remote_id, output_file)
    except Exception as e:
        print("cannot download data via remote broker",file=sys.stderr)
        sys.exit(str(e))

if __name__ == '__main__':
    __main__()
