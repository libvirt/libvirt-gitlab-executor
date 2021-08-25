import os

from setuptools import setup, Command


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system("rm -vrf ./build ./dist ./*.pyc ./*.egg-info")


setup(
    name="libvirt-gci",
    version="0.1",
    packages=["provisioner"],
    package_dir={"": "src"},
    scripts=["bin/libvirt-gci"],
    author="Erik Skultety",
    author_email="eskultet@redhat.com",
    description="GitLab CI libvirt VM provisioner",
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)"
    ],
    cmdclass={
        "clean": CleanCommand,
    }
)
