# ssh.py - module containing simple paramiko library wrapper
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import paramiko
import sys
from pathlib import Path


log = logging.getLogger(__name__)


def get_user_ssh_keys(username=None):
    pubkeys = []
    for entry in Path(Path.home(), ".ssh").iterdir():
        if entry.suffix != ".pub":
            continue
        with open(entry) as fd:
            pubkeys.append(fd.readline())

    return pubkeys


class SSHConn:
    """
    Wrapper class over the Paramiko library.

    A simple wrapper implementing a few basic & common operations with the
    Paramiko library. If, for some reason, you need to work directly with
    Paramiko, use the self._client attribute.
    """

    class _IgnorePolicy(paramiko.MissingHostKeyPolicy):
        def missing_host_key(self, client, hostname, key):
            return

    def __init__(self, hostname, username, key_filepath, timeout=30):
        log.debug(f"Establishing SSH connection: hostname={hostname},"
                  f"username={username},key_filepath={key_filepath}")

        self.hostname = hostname

        ssh_key_path = key_filepath
        if isinstance(key_filepath, Path):
            ssh_key_path = key_filepath.as_posix()

        self._client = paramiko.SSHClient()
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(self._IgnorePolicy)
        self._client.connect(hostname=self.hostname,
                             username="gitlab-runner",
                             key_filename=ssh_key_path,
                             timeout=timeout)

    def upload(self, src, dst):
        """Uploads a file to a remote location using SFTP."""

        log.debug(f"Uploading '{src}' to '{dst}'")

        sftp = self._client.open_sftp()
        sftp.put(src, dst)
        sftp.close()

    def exec(self, command, command_args=[]):
        """
        Executes a command on the remote side over SSH.

        If the command happens to be a script, the script first needs to be
        copied to the remote side (see SSHConn.upload()).
        """

        # Paramiko is particularly bad at running long-lasting command in a
        # shell environment, e.g. the 'exec_command' method is always
        # non-blocking and the channel is closed immediately so the script
        # output would never be seen. Simply instructing it to get a PTY
        # doesn't help and without pretty much low level handling the channel
        # is always closed.

        log.debug(f"Opening SSH transport channel to '{self.hostname}'")

        cmd_str = f"{command} {' '.join(command_args)}"

        transport = self._client.get_transport()
        channel = transport.open_session()
        channel.set_combine_stderr(True)

        log.debug(f"Executing command '{cmd_str}' on '{self.hostname}'")
        channel.exec_command(cmd_str)

        data = channel.recv(1024)
        while data:
            sys.stdout.write(data.decode())
            data = channel.recv(1024)

        if channel.recv_exit_status() != 0:
            raise Exception(f"Command execution failed ({cmd_str})")
