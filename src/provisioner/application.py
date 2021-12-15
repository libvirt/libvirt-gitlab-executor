# application.py - module containing the libvirt-gci application code
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging

from provisioner.configmap import ConfigMap
from provisioner.singleton import Singleton

log = logging.getLogger(__name__)


class Application(metaclass=Singleton):
    def __init__(self, cli_args):
        # initialize the global configuration map singleton object
        ConfigMap(**cli_args)

    def _action_prepare(self):
        pass

    def _action_run(self):
        pass

    def _action_cleanup(self):
        pass

    def run(self):
        cb = self.__getattribute__("_action_" + ConfigMap()["action"])
        cb()
