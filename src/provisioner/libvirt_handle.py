# libvirt_handle.py - module containing the libvirt wrapper
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import libvirt
import logging
import socket
import sys
import xml.etree.ElementTree as xmlparser


log = logging.getLogger(__name__)


class LibvirtHandle:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(LibvirtHandle, cls).__new__(cls)
        return cls.__instance

    def __init__(self, uri="qemu:///system"):
        def nop_error_handler(_T, iterable):
            return None

        # Disable libvirt's default console error logging
        libvirt.registerErrorHandler(nop_error_handler, None)
        self.conn = libvirt.open(uri)

    def __del__(self):
        self.conn.close()

    def _get_base_image(self, name, poolname):
        log.debug(f"Looking up base image: name={name},poolname={poolname}")

        pool = self.conn.storagePoolLookupByName(poolname)
        vol = None
        for vol in pool.listAllVolumes():
            if name == vol.name():
                return vol
        else:
            raise Exception(f"Base image '{name}' not found")

    def create_volume(self, volname, size, distro, poolname="default"):
        log.debug(f"Creating overlay volume: poolname={poolname},"
                  f"distro={distro},volname={volname},size={size}")

        template = """
        <volume>
          <name>{name}</name>
          <capacity unit='G'>{size}</capacity>
          <target>
            <format type='qcow2'/>
          </target>
          <backingStore>
            <path>{backing_vol_path}</path>
            <format type='{backing_vol_format}'/>
          </backingStore>
        </volume>
        """

        # get the base image for the volume
        base_img_name = distro + ".qcow2"
        base_image_vol = self._get_base_image(base_img_name, "base_imgs")

        # parse the base image volume to extract data we'll need to fill in
        # the backing store XML element
        xml_root_node = xmlparser.fromstring(base_image_vol.XMLDesc())
        target_node = xml_root_node.find("target")
        backing_vol_format = target_node.find("format").get("type")
        backing_vol_path = target_node.find("path").text

        # finally create the overlay storage volume
        pool = self.conn.storagePoolLookupByName(poolname)
        pool.createXML(template.format(name=volname, size=size,
                                       backing_vol_path=backing_vol_path,
                                       backing_vol_format=backing_vol_format))

    def wait_for_machine(self, name):
        log.debug(f"Looking up domain object: name={name}")

        channel_path = ""
        domain = self.conn.lookupByName(name)

        xml_root_node = xmlparser.fromstring(domain.XMLDesc())
        devices_node = xml_root_node.find("devices")
        for channel in devices_node.findall("channel"):
            target_node = channel.find("target")
            source_node = channel.find("source")
            if target_node.get("name") == "call_home.network":
                channel_path = source_node.get("path")

        log.debug(f"Opening channel '{channel_path}' to listen")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(channel_path)

        try:
            sock.settimeout(30)
            sock.recv(1)
        except socket.timeout:
            print("socket timeout reached")
            sys.exit(1)

    def cleanup_machine(self, name):
        try:
            log.debug("Destroying domain '{name}'")

            domain = self.conn.lookupByName(name)
            domain.destroy()
        except libvirt.libvirtError as ex:
            if ex.get_error_code() != libvirt.VIR_ERR_NO_DOMAIN:
                raise

    def cleanup_storage(self, name):
        pool_default = self.conn.storagePoolLookupByName("default")
        try:
            log.debug("Destroying storage for '{name}'")

            volume = pool_default.storageVolLookupByName(name)
            volume.delete()
        except libvirt.libvirtError as ex:
            if ex.get_error_code() != libvirt.VIR_ERR_NO_STORAGE_VOL:
                raise
