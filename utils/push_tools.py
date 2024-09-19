import os
import subprocess
import xml.etree.ElementTree as ET



def get_version(fname):
    try:
        with open(fname, 'r') as file:
            xml_string = file.read()

            # Parse the XML string
        root = ET.fromstring(xml_string)
        return root.get('version')
    except Exception as e:
        return ""
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Transfer files from local to remote server using SSH")

    parser.add_argument(
        "--source-directory",
        type=str,
        required=True,
        help="Path to the local directory you want to transfer"
    )

    parser.add_argument(
        "--ssh-key-path",
        type=str,
        required=True,
        help="Path to the SSH private key (id_rsa)"
    )

    parser.add_argument(
        "--remote-user",
        type=str,
        required=True,
        help="Username for the remote server"
    )

    parser.add_argument(
        "--remote-host",
        type=str,
        required=True,
        help="Hostname or IP address of the remote server"
    )

    parser.add_argument(
        "--remote-directory",
        type=str,
        required=True,
        help="Path to the remote directory where you want to transfer the files"
    )

    return parser.parse_args()

def file_to_remote(args, source_file):
    # Construct the SCP command with SSH options
    scp_command = [
        'rsync',
        '-e', f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null  -i {args.ssh_key_path}",  # Ignore new host warning
        '--rsync-path','sudo rsync',
        source_file,
        f'{args.remote_user}@{args.remote_host}:{args.remote_directory}'
    ]

    # Run the SCP command
    subprocess.run(scp_command, check=True)
    print(f'File {source_file} successfully copied to {args.remote_host}:{args.remote_directory}')

def dir_to_remote(args, source_dir):
    scp_command = [
        'rsync',
        '-e', f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null  -i {args.ssh_key_path}",  # Ignore new host warning
        '--rsync-path','sudo rsync',
        source_dir,
        f'{args.remote_user}@{args.remote_host}:{args.remote_directory}'
    ]

    # Run the SCP command
    subprocess.run(scp_command, check=True)
    print(f'File {source_dir} successfully copied to {args.remote_host}:{args.remote_directory}')


if __name__ == "__main__":
    args = parse_arguments()
    for fname in os.listdir(args.source_directory):
        path = os.path.join(args.source_directory,fname)
        if "dev" in get_version(path):
            file_to_remote(args, path)
    dir_to_remote(args, os.path.join(args.source_directory,"test-data"))
