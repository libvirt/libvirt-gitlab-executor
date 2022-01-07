# application.py - module containing the libvirt-gci application code
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import os

from pathlib import Path

from provisioner.configmap import ConfigMap
from provisioner.machine import Machine
from provisioner.singleton import Singleton

log = logging.getLogger(__name__)


class Application(metaclass=Singleton):
    def __init__(self, cli_args):
        # initialize the global configuration map singleton object
        configmap = ConfigMap(**cli_args)

        # GitLab will set these with every job
        project = os.environ.get("CUSTOM_ENV_CI_PROJECT_NAME")
        job_id = os.environ.get("CUSTOM_ENV_CI_JOB_ID")
        distro = os.environ.get("CUSTOM_ENV_DISTRO")

        if distro is not None:
            configmap["distro"] = distro

        configmap["project"] = project
        configmap["job_id"] = job_id

    def _get_machine_name(self):
        configmap = ConfigMap()
        name = configmap["machine"]
        project = configmap["project"]
        distro = configmap["distro"]
        job_id = configmap["job_id"]

        # GitLab-driven provision
        if all([project, distro, job_id]):
            name = f"gitlab-{project}-{distro}-{job_id}"
        else:
            # Manual provision
            if configmap["action"] == "prepare":
                if distro is None:
                    raise Exception("No distro specified for manual execution")

                if name is None:
                    import random
                    from string import ascii_letters

                    randstr = "".join(random.sample(ascii_letters, 8))
                    name = f"{distro}-{randstr}"

            elif name is None:
                raise Exception("No machine name specified for manual execution")

        log.debug(f"Machine will be called '{name}'")
        return name

    def _action_prepare(self):
        configmap = ConfigMap()

        machine = Machine(self._get_machine_name())
        machine.provision(configmap["distro"])
        machine.connect(configmap["ssh_key_file"])

    def _action_run(self):
        configmap = ConfigMap()

        cmd_str = configmap["executable"]
        cmd_args = configmap["exec_args"]
        machine = Machine(self._get_machine_name())
        conn = machine.connect(configmap["ssh_key_file"])

        if configmap["script"]:
            basename = Path(configmap["executable"]).name

            with open(configmap["executable"], "r"):
                # NADA - check that the file exists and we can read it
                pass

            dest = f"/tmp/{basename}"
            conn.upload(configmap["executable"], dest)
            cmd_str = "/bin/bash"
            cmd_args = [dest] + configmap["exec_args"]

        conn.exec(cmd_str, cmd_args)

    def _action_cleanup(self):
        Machine(self._get_machine_name()).teardown()

    def run(self):
        cb = self.__getattribute__("_action_" + ConfigMap()["action"])
        cb()