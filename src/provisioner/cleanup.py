#!/usr/bin/env python3

import os

from provisioner.machine import Machine

distro = os.environ.get("CUSTOM_ENV_DISTRO")
job_id = os.environ.get("CUSTOM_ENV_CI_JOB_ID")
project = os.environ.get("CUSTOM_ENV_CI_PROJECT_NAME")

machine = Machine(f"gitlab-{project}-{distro}-{job_id}")
machine.cleanup()
