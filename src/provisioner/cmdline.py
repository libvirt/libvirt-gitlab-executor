# cmdline.py - module containing the command line parser
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse


class CmdLine:
    """
    Command line parser.

    Caller can register their own callback for each of the arguments with the``
    'register_cb' method.
    """

    def __init__(self):
        self._parsers = {}

        self._parsers["__main__"] = argparse.ArgumentParser(
            conflict_handler="resolve",
            description="GitLab CI libvirt custom executor wrapper tool",
        )

        self._parsers["__main__"].add_argument(
            "--debug",
            help="display debugging information",
            action="store_true",
        )

        subparsers = self._parsers["__main__"].add_subparsers(metavar="COMMAND",
                                                              dest="action")
        subparsers.required = True

        sshkeyopt = argparse.ArgumentParser(add_help=False)
        sshkeyopt.add_argument(
            "--ssh-key-file",
            metavar="PATH",
            help="path to SSH private key"
        )

        for command in ["prepare", "run", "cleanup"]:
            parser = subparsers.add_parser(
                command,
                help=f"GitLab {command} stage parser",
                parents=[sshkeyopt]
            )

            parser.add_argument(
                "-m", "--machine",
                help="machine instance to operate on",
            )

            self._parsers[command] = parser

        self._parsers["prepare"].add_argument(
            "-d", "--distro",
            help="what OS distro base image to use for provisioning",
        )

        self._parsers["run"].add_argument(
            "executable",
            nargs="?",
            help="Absolute path to the executable",
        )
        self._parsers["run"].add_argument(
            "exec_args",
            nargs="*",
            help="Arguments to be passed to the executable",
        )
        self._parsers["run"].add_argument(
            "--script",
            help="Upload and execute a script instead of a command",
            action="store_true",
        )

    def parse(self):
        """Parses the command line arguments (Argparse entry point)."""

        return self._parsers["__main__"].parse_args()

    def register_cb(self, command, cb):
        """Registers a callback for a subcommand."""

        self._parsers[command].set_defaults(func=cb)
