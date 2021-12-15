# config.py - module containing the project's configmap definition
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging

from provisioner.singleton import Singleton

log = logging.getLogger(__name__)


class ConfigMap(metaclass=Singleton):

    def __init__(self, **kwargs):
        opts = [
            "action",
            "debug",
            "distro",
            "executable",
            "exec_args",
            "machine",
            "script",
            "ssh_key_file",
        ]

        self._values = dict(zip(opts, [None] * len(opts)))
        self._values.update(kwargs)

    def __contains__(self, item):
        return item in self._values

    def __getitem__(self, key):
        if type(key) is not str:
            raise TypeError

        return self._values[key]

    def __setitem__(self, key, value):
        if type(key) is not str:
            raise TypeError

        self._values[key] = value
