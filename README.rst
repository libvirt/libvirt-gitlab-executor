=======================
libvirt-gitlab-executor
=======================

This repository provides a simple tool called ``libvirt-gci`` which wraps the
necessary functionality in order to make use of GitLab's custom executor
feature and allows GitLab CI pipeline provision and execute job workloads in
VMs running on any host system you designated for this use.


Prerequisites
=============
Not all of the following packages need to be installed necessarily, especially
if you want to bring your own machine templates (and not create ones with
lcitool), but since libvirt is used underneath for the custom executor feature,
at least ``libvirt`` related packages and ``virt-install`` are needed.  The
rest is only needed if you also want to prepare the template VMs using `lcitool
<https://gitlab.com/libvirt/libvirt-ci>`_, see the whole list of requirements
below.

*Packages*:

* ``ansible``
* ``git``
* ``libvirt-daemon-qemu``
* ``libvirt-driver-network``
* ``libvirt-daemon-config-network``
* ``libvirt-nss``
* ``python3-ansible-runner``
* ``python3-libvirt``
* ``python3-pyyaml``
* ``virt-install``


Creating base image templates
=============================

In order to save storage for concurrent VMs, base image templates need to
be created for the worker VMs that the GitLab executor will spawn. The base
images will later be used with a QCOW2 overlay image for each GitLab VM
instance provisioned. If you already have your VMs that you'd like to use as a
template, you can skip the next *lcitool* part.


Lcitool
-------

One of the options to provision a machine which will serve as a template is by
using `lcitool <https://gitlab.com/libvirt/libvirt-ci>`_:

(1) Clone the lcitool git repository

::

    $ git clone https://gitlab.com/libvirt/libvirt-ci.git

(2) Follow the instructions to install/run lcitool in the README file inside the
    lcitool's repo

(3) Install a target OS instance, in this case an instance of Fedora 34. Note
    that the user running this command needs to be in the libvirt group OR use
    sudo

::

    $ lcitool install my-fedora --target fedora-35 --wait

(4) Update the installed instance with dependencies for a given project, in this
    example - *libvirt-tck+runtime*, see lcitool's README on how this works

::

    $ lcitool update libvirt-tck+runtime


Creating a template
-------------------

Now that a machine is ready to become a template, run the following to create
the base image. Technically it's not needed to run the following with root
privileges, but since the VM image is located in /var/lib/libvirt/base_imgs
which requires privileges, it would be necessary to adjust the permissions, so
that libguestfs tools can access the images in order to create templates:

::

    $ sudo make_base_image/make_base_image.sh vm1 vm2 vmN

You have now successfully created base images for your VMs and can use them with
GitLab's custom executor.


Utilizing GitLab's custom executor
----------------------------------

To set-up the gitlab-runner agent correctly, follow the official documentation
`here <https://docs.gitlab.com/runner/executors/custom.html>`_. For the stage
scripts, you're going to use the following in your gitlab-runner config:

::

    ...
    prepare_exec = "/home/<user>/.local/bin/libvirt-gci"
    prepare_args = [ "prepare" ]
    run_exec = "/home/<user>/.local/bin/libvirt-gci"
    run_args = ["run", "--script"]
    cleanup_exec = "/home/<user>/.local/bin/libvirt-gci"
    cleanup_args = ["cleanup"]


TIP: Don't forget to set the ``concurrent`` argument for the gitlab-runner agent
to make sure several VM jobs can run in parallel on your host.


Provisioning a test instance manually
-------------------------------------

If you experience failures using the setup with GitLab it might be beneficial
to be able to provision an instance manually the same way GitLab does. The
reason for that is simple - GitLab always cleans up the machine after the job
is finished, no matter if it passed or failed. So naturally, one would like to
poke around the machine to see what could have caused the failure. One way
of doing it is defining the same environment variables GitLab uses in their CI
pipeline workflow.

::

    $ CUSTOM_ENV_CI_PROJECT_NAME=libvirt \
      CUSTOM_ENV_CI_JOB_ID=12345 \
      CUSTOM_ENV_DISTRO=fedora-34 \
      libvirt-gci prepare

The other is to omit them and use the following CLI options:

::

    $ libvirt-gci prepare --distro <template_os> [--machine <instance_name>]

Note that both of the above expect that you have installed the project binary
using the ``setup.py`` script.

Once you're done playing with the instance, you can destroy it with the same
tool using either of the following ways depending on which way you provisioned
the instance:

::

    $ CUSTOM_ENV_CI_PROJECT_NAME=libvirt \
      CUSTOM_ENV_CI_JOB_ID=12345 \
      CUSTOM_ENV_DISTRO=fedora-34 \
      libvirt-gci cleanup

or

::

    $ libvirt-gci cleanup --machine <instance_name>


License
=======

The contents of this repository are distributed under the terms of the GNU
General Public License, version 2 (or later). See the ``COPYING`` file for full
license terms and conditions.
