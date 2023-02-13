import pyoncat
import argparse
import os
import sys
import scp
import paramiko
import jwt
import socket
import json
import datetime

from msal import ConfidentialClientApplication

ONCAT_URL = "https://oncat.ornl.gov"
SNS_STORAGE_HOST = "calvera.ornl.gov"
MAX_PASSWD_STR_LENGTH = 511

token = os.environ["_GALAXY_OIDC_ID_TOKEN"]


def refresh_token_if_needed():
    global token

    decoded = jwt.decode(token, options={"verify_signature": False})

    now = datetime.datetime.timestamp(datetime.datetime.now())
    if decoded['exp'] < now:
        refresh_token = os.environ["_GALAXY_OIDC_REFRESH_TOKEN"]
        oidc_config = json.loads(args.oidc_config)

        tenant_id = oidc_config['url'].split("/")[3]
        app = ConfidentialClientApplication(
            oidc_config['client_id'],
            client_credential=oidc_config['client_secret'],
            authority="https://login.microsoftonline.com/" + tenant_id)

        res = app.acquire_token_by_refresh_token(refresh_token, scopes=["https://graph.microsoft.com/.default"])
        token = res['id_token']


def fix_ipts(input_string):
    if not input_string.upper().startswith("IPTS-"):
        return "IPTS-" + input_string
    return input_string


def interaction_handler(_title, _instructions, prompt_list):
    global token
    resp = []
    for pr in prompt_list:
        if pr[0].strip() == "Next:":
            if len(token) == 0:
                resp.append('token_end')
            elif len(token) > MAX_PASSWD_STR_LENGTH:
                resp.append(token[0:MAX_PASSWD_STR_LENGTH])
                token = token[MAX_PASSWD_STR_LENGTH:]
            else:
                resp.append(token)
                token = ''
        else:
            if len(token) > MAX_PASSWD_STR_LENGTH:
                resp.append(token[0:MAX_PASSWD_STR_LENGTH])
                token = token[MAX_PASSWD_STR_LENGTH:]
    return tuple(resp)


def copy_datafile(input: str, output: str):
    try:
        refresh_token_if_needed()
    except:
        sys.exit("Cannot refresh token, please re-login to Calvera")
    username, _ = jwt.decode(token, options={"verify_signature": False})['preferred_username'].split("@", 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SNS_STORAGE_HOST, 22))
    ts = paramiko.Transport(sock)
    ts.start_client(timeout=10)
    ts.auth_interactive(username, interaction_handler)
    scp_client = scp.SCPClient(ts)
    scp_client.get(remote_path=input, local_path=output)


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--instrument", type=str, required=True, help="Instrument name")
parser.add_argument("-f", "--facility", type=str, required=True, help="Facility name")
parser.add_argument("-I", "--ipts", type=str, help="IPTS number")
parser.add_argument("-r", "--run", type=str, help="Run number")
parser.add_argument("-o", "--output", type=str, help="Output file")
parser.add_argument("-c", "--oidc-config", type=str, help="OIDC configuration")

args = parser.parse_args()

oncat = pyoncat.ONCat(ONCAT_URL)

projection = [
    "indexed.run_number",
    "path",
    "ext"
]

if not args.ipts:
    experiments = oncat.Experiment.list(facility=args.facility, instrument=args.instrument)
    with open(args.output, 'w') as f:
        for experiment in experiments:
            if experiment.get("title"):
                f.write("%s\t%s\t%s" % (experiment.get("name"), experiment.get("title"), experiment.get("")))
elif not args.run:
    with open(args.output, 'w') as f:
        datafiles = oncat.Datafile.list(experiment=fix_ipts(args.ipts), facility=args.facility,
                                        instrument=args.instrument, projection=projection, exts=[".nxs.h5"])
        for datafile in datafiles:
            f.write("%s\t%s" % (datafile.get("indexed.run_number"), datafile.get("location")))
else:
    datafiles = oncat.Datafile.list(experiment=fix_ipts(args.ipts), facility=args.facility, instrument=args.instrument,
                                    projection=projection, exts=[".nxs.h5"], ranges_q="indexed.run_number:" + args.run)
    if len(datafiles) != 1:
        print("Invalid run number")
        sys.exit(1)
    copy_datafile(datafiles[0].get("location"), args.output)
