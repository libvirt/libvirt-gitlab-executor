# cloud_init.py - module wrapping basic cloud init setup
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import socket
import threading
import urllib.parse

from http.server import BaseHTTPRequestHandler, HTTPServer

from provisioner.ssh import get_user_ssh_keys


log = logging.getLogger(__name__)


def get_user_data(hostname, phone_home_address):
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

    host = phone_home_address[0]
    port = phone_home_address[1]
    phone_home = {
        "url": f"http://{host}:{port}/$INSTANCE_ID",
        "post": "all",
    }

    user_data = {}
    user_data["users"] = [gitlab_runner]
    user_data["chpasswd"] = chpasswd
    user_data["fqdn"] = hostname
    user_data["phone_home"] = phone_home

    log.debug(f"Cloud-init user data: {user_data}")

    return user_data


class _MyHTTPHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests to the phone home cloud-init server."""

    def do_POST(self):
        if not self.path.strip("/") == "nocloud":
            self.send_response(404)
        else:
            content_length = int(self.headers.get("content-length"))
            post_query_string = self.rfile.read(content_length).decode("utf-8")
            post_data = urllib.parse.parse_qs(post_query_string)

            if self.server.instance_hostname != post_data["hostname"][0]:
                self.send_response(403)
            else:
                self.server.instance_phoned_home = True
                self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args, **kwargs):
        # disable the default request handler logging
        pass


class _MyHTTPServer(HTTPServer):
    def __init__(self, instance_hostname, address):
        self.instance_hostname = instance_hostname
        self.instance_phoned_home = False
        super().__init__(address, _MyHTTPHandler)

    def run(self):
        while not self.instance_phoned_home:
            self.handle_request()


class CloudInitPhoneHomeServer():
    """
    Implements an asynchronous HTTP cloud-init phone home server.

    Waits for a cloud-init powered instance to use the phone home module.
    This class provides an interface where the HTTP server runs asynchronously.
    In order to check whether the instance has already phoned home, the caller
    needs to use the 'wait()' method which blocks until the condition
    (the instance phoned home) was met.
    """

    @property
    def address(self):
        return self._httpd.server_address

    def __init__(self, instance_hostname, address=None):
        """Initialize the server.
        :param address: follows the AF_INET family address specification -->
                        (host, port) tuple; if no address was specified, both
                        host IP and port the server will listen on will be
                        selected automatically
        :param instance_id: identification of the instance that is expected
                            to call back via cloud-init
        """

        def server_run(httpd):
            log.debug("Server thread created, running HTTP server on "
                      f"{httpd.server_name}:{httpd.server_port}")

            with httpd:
                httpd.run()

        log.debug("Creating HTTP phone home server")

        if address is None:
            # port 0 means the OS will pick the first available port
            address = (socket.gethostbyname(socket.getfqdn()), 0)

        self._httpd = _MyHTTPServer(instance_hostname, address)
        self._httpd_thread = threading.Thread(target=server_run,
                                              args=(self._httpd, ),
                                              daemon=True)
        self._httpd_thread.start()
        self._address = None
        self._instance = instance_hostname

    def wait(self):
        """Synchronous blocking wait until the machine instance phones home."""

        timeout = 120

        log.debug(f"Waiting for '{self._instance}' to phone home ({timeout}s)")
        self._httpd_thread.join(timeout=timeout)

        if self._httpd_thread.is_alive():
            raise Exception(f"Instance did not phone home (timeout: {timeout}s)")
