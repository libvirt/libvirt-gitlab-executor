# cloud_init.py - module wrapping basic cloud init setup
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging

from provisioner.ssh import get_user_ssh_keys


log = logging.getLogger(__name__)


def get_user_data(hostname):
    """Generates simple cloud-init user data."""

    gitlab_runner = {
        "name": "gitlab-runner",
        "sudo": "ALL=(ALL) NOPASSWD:ALL",
        "ssh_authorized_keys": get_user_ssh_keys(),
    }

    chpasswd = {
        "list": ["root:RANDOM", "gitlab-runner:RANDOM"],
        "expire": False,
    }

    user_data = {}
    user_data["users"] = [gitlab_runner]
    user_data["chpasswd"] = chpasswd
    user_data["fqdn"] = hostname

    log.debug(f"Cloud-init user data: {user_data}")

    return user_data
