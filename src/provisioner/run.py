#!/usr/bin/env python3

import os
import sys
from pathlib import Path

from provisioner.ssh import SSHConn

project = os.environ.get("CUSTOM_ENV_CI_PROJECT_NAME")
distro = os.environ.get("CUSTOM_ENV_DISTRO")
job_id = os.environ.get("CUSTOM_ENV_CI_JOB_ID")

currentdir = Path(sys.argv[0]).parent
gitlab_script_name = sys.argv[1]
gitlab_current_stage = sys.argv[2]
scp_dst = f"/tmp/{gitlab_current_stage}"
host = f"gitlab-{project}-{distro}-{job_id}"

ssh_conn = SSHConn(host, "gitlab-runner", Path(currentdir, "id_ed25519"))
ssh_conn.upload(gitlab_script_name, scp_dst)
rc = ssh_conn.exec("/bin/bash", [scp_dst])

sys.exit(rc)
