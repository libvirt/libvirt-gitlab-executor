# util.py - module containing utility functions
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import pwd


def get_username():
    return pwd.getpwuid(os.getuid()).pw_name


