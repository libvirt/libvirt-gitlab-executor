#!/usr/bin/env python3

import logging
import os
import sys

from provisioner.machine import Machine
from provisioner.logger import LevelFormatter

log_level_formats = {
    logging.DEBUG: "[%(levelname)s] %(module)s:%(funcName)s:%(lineno)d: %(message)s",
    logging.ERROR: "[%(levelname)s]: %(message)s",
}

custom_formatter = LevelFormatter(log_level_formats)
custom_handler = logging.StreamHandler(stream=sys.stderr)
custom_handler.setFormatter(custom_formatter)

log = logging.getLogger()
log.addHandler(custom_handler)

project = os.environ.get("CUSTOM_ENV_CI_PROJECT_NAME")
distro = os.environ.get("CUSTOM_ENV_DISTRO")
job_id = os.environ.get("CUSTOM_ENV_CI_JOB_ID")

name = f"gitlab-{project}-{distro}-{job_id}"

machine = Machine(name)
machine.provision(distro)
machine.ready()
