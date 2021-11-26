#!/usr/bin/env python3

with open("/dev/virtio-ports/call_home.network", "wb") as fd:
    fd.write(bytes([True]))
