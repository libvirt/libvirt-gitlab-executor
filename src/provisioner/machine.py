# machine.py - module containing VM abstraction class
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import subprocess
import sys

from pathlib import Path

from provisioner import util
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
        m.wait()   # optional, but connections will fail until networking is up
        conn = m.connect()  # verifies that jobs can be sent to the VM over SSH
        conn.upload(script, remote_dest)
        rc = conn.exec(cmd, [cmd_args])
    """

    def __init__(self, name):
        self.name = name

    def wait(self):
        """
        Wait until networking is up and running in the VM.

        Uses a virtio channel over a UNIX socket and a simple agent installed
        in the VM to know when the machine becomes online and ready for
        connections.
        """

        log.debug(f"Waiting for machine '{self.name}' to become online")

        libvirt_handle = LibvirtHandle()
        libvirt_handle.wait_for_machine(self.name)

    def connect(self, ssh_key_path=None):
        """Opens an SSH channel to the VM."""

        if ssh_key_path is None:
            homedir = util.get_homedir(util.get_username())
            ssh_key_path = Path(homedir, ".ssh/id_ed25519")

        try:
            log.debug(f"Connecting to '{self.name}'")
            conn = SSHConn(hostname=self.name,
                           username="gitlab-runner",
                           key_filepath=ssh_key_path)
        except Exception as ex:
            print(ex, file=sys.stderr)
            sys.exit(1)

        return conn

    def provision(self, distro, size=50):
        """
        Provisions a new transient VM instance from an existing base image.

        The instance is created with a virtio UNIX channel so that @wait can
        block until the VM is online.
        """

        log.debug(f"Provisioning machine '{self.name}'")

        username = util.get_username()

        # create the storage for the VM first
        libvirt_handle = LibvirtHandle()
        path = libvirt_handle.create_volume(self.name, size, distro)

        # the bootstrap service will signal that the machine is online through
        # this channel
        channel_name = "call_home.network"
        channel_args = [
            "type=unix",
            "mode=bind",
            f"path=/tmp/{self.name}.channel",
            "source.seclabel.model=dac",
            "source.seclabel.relabel=yes",
            f"source.seclabel.label={username}:qemu",
            "target.type=virtio",
            f"target.name={channel_name}"
        ]
        channel_args_str = ",".join(channel_args)

        cmd = [
            "virt-install",
            "--connect", "qemu:///system",
            "--name", self.name,
            "--disk", f"vol=default/{self.name},bus=virtio",
            "--vcpus", "4",
            "--ram", "8192",
            "--machine", "q35",
            "--network", "network=default,model=virtio",
            "--graphics", "none",
            "--sound", "none",
            "--channel", f"{channel_args_str}",
            "--transient",
            "--console", "pty",
            "--noautoconsole",
            "--import"
        ]

        subprocess.check_call(cmd)

    def teardown(self):
        """Cleans up the VM instance along with its block storage overlay."""

        log.debug(f"Cleaning up '{self.name}' resources")

        libvirt_handle = LibvirtHandle()
        libvirt_handle.cleanup_machine(self.name)
        libvirt_handle.cleanup_storage(self.name)
