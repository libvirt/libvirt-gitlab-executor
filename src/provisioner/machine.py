# machine.py - module containing VM abstraction class
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import os
import subprocess
import yaml

from pathlib import Path
from tempfile import NamedTemporaryFile

from provisioner import cloud_init
from provisioner.configmap import ConfigMap
from provisioner.libvirt_handle import LibvirtHandle
from provisioner.ssh import SSHConn


log = logging.getLogger(__name__)


class Machine:
    """
    This class serves as a simple abstraction over a virtual machine.

    The prerequisite to provisioning a new VM is that a base image of the
    specific distribution already exists in the libvirt land.

    The usual flow of actions is as follow:
        m = Machine(name)
        m.provision(distro)
        conn = m.connect(ssh_key_file)  # verifies that jobs can be sent to the
                                          VM over SSH
        conn.upload(script, remote_dest)
        rc = conn.exec(cmdlinestr)
    """

    def __init__(self, name):
        self.name = name

    def connect(self, ssh_key_path=None):
        """
        Opens an SSH channel to the VM.

        Will use @ssh_key_path for authentication. If no SSH identity was
        provided, a default one '~/.ssh/id_ed25519' will be tried.

        :param ssh_key_path: path to the SSH key as string
        """

        if ssh_key_path is None:
            ssh_key_path = Path(Path.home(), ".ssh/id_ed25519")

        try:
            log.debug(f"Connecting to '{self.name}'")
            conn = SSHConn(hostname=self.name,
                           username="gitlab-runner",
                           key_filepath=ssh_key_path)
        except Exception as ex:
            raise Exception(f"Failed to connect to {self.name}: {ex}")

        return conn

    def _dump_user_data(self, user_data):
        tempfile = NamedTemporaryFile(delete=False,
                                      prefix=(self.name + "-cloud-config"))

        with open(tempfile.name, "w") as fd:
            # nasty hack to force PyYAML not to break long lines by default
            from math import inf

            # must write the header first, otherwise cloud-init will ignore the file
            fd.write("#cloud-config\n")
            fd.write(yaml.dump(user_data, width=inf))
        return tempfile.name

    def provision(self, distro, size=50):
        """
        Provisions a new transient VM instance from an existing base image.

        The instance is created with a virtio UNIX channel so that @wait can
        block until the VM is online.

        :param distro: which distro template to use as string
        :param size: capacity of the underlying storage in GB, default is 50
        """

        log.debug(f"Provisioning machine '{self.name}'")

        # create the storage for the VM first
        libvirt_handle = LibvirtHandle()
        path = libvirt_handle.create_volume(self.name, size, distro)

        # Start the cloud-init phone home server
        server = cloud_init.CloudInitPhoneHomeServer(self.name)
        user_data = cloud_init.get_user_data(self.name, server.address)
        user_data_file = self._dump_user_data(user_data)

        cmd = [
            "virt-install",
            "--connect", "qemu:///system",
            "--os-variant", "unknown",
            "--name", self.name,
            "--disk", f"vol=default/{self.name},bus=virtio",
            "--vcpus", "4",
            "--ram", "8192",
            "--machine", "q35",
            "--network", "network=default,model=virtio",
            "--graphics", "none",
            "--sound", "none",
            "--transient",
            "--console", "pty",
            "--noautoconsole",
            "--cloud-init", f"user-data={user_data_file}",
            "--import"
        ]

        if not ConfigMap()["debug"]:
            cmd.append("--quiet")

        subprocess.check_call(cmd)
        try:
            server.wait()
        except Exception:
            raise
        finally:
            os.unlink(user_data_file)

    def teardown(self):
        """Cleans up the VM instance along with its block storage overlay."""

        log.debug(f"Cleaning up '{self.name}' resources")

        libvirt_handle = LibvirtHandle()
        libvirt_handle.cleanup_machine(self.name)
        libvirt_handle.cleanup_storage(self.name)
