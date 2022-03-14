# libvirt_handle.py - module containing the libvirt wrapper
#
# Copyright (C) 2021 Red Hat, Inc.
#
# SPDX-License-Identifier: GPL-2.0-or-later

import libvirt
import logging
import xml.etree.ElementTree as xmlparser


log = logging.getLogger(__name__)


class LibvirtHandle:
    """Convenience wrapper for the libvirt library."""

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
        """
        Looks up the template base image.

        :param name: Name of the base image template as string
        :param poolname: Name of the storage pool to search as string
        """

        log.debug(f"Looking up base image: name={name},poolname={poolname}")

        pool = self.conn.storagePoolLookupByName(poolname)
        vol = None
        for vol in pool.listAllVolumes():
            if name == vol.name():
                return vol
        else:
            raise Exception(f"Base image '{name}' not found")

    def create_volume(self, volname, size, distro, poolname="default"):
        """
        Creates an overlay volume for the given machine.

        :param volname: name of the volume to be created as string
        :param size: capacity of the volume as string/int
        :param distro: which distro template image to look for as string
        :param poolname: which libvirt storage pool to search for the template
                         image as string
        """

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

    def cleanup_machine(self, name):
        """
        Destroy a libvirt machine.

        This method will look up a VM given a @name and will destroy it.

        :param name: name of the machine to destroy as string

        """

        try:
            log.debug("Destroying domain '{name}'")

            domain = self.conn.lookupByName(name)
            domain.destroy()
        except libvirt.libvirtError as ex:
            if ex.get_error_code() != libvirt.VIR_ERR_NO_DOMAIN:
                raise

    def cleanup_storage(self, name):
        """
        Clean up overlay storage for a machine.

        The machine '@name' should have been destroyed prior to calling this
        method already.

        :param name: name of the machine storage needs to be cleanup up for as
                     string
        """

        pool_default = self.conn.storagePoolLookupByName("default")
        try:
            log.debug("Destroying storage for '{name}'")

            volume = pool_default.storageVolLookupByName(name)
            volume.delete()
        except libvirt.libvirtError as ex:
            if ex.get_error_code() != libvirt.VIR_ERR_NO_STORAGE_VOL:
                raise
