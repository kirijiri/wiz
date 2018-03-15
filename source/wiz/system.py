# :coding: utf-8

import os
import sys
import platform

import wiz.exception


def query_platform():
    """Return current platform.

    Raise :exc:`wiz.exception.UnsupportedPlatform` if platform is not supported.

    """
    name = platform.system().lower()
    if name == "linux":
        return LinuxPlatform()
    elif name == "darwin":
        return MacOsPlatform()
    elif name == "windows":
        return WindowsPlatform()

    raise wiz.exception.UnsupportedPlatform(name)


class LinuxPlatform(object):
    """Linux platform."""

    def name(self):
        """Return platform name."""
        return "linux"

    def arch(self):
        """Return architecture ("x86_64" or "i386")."""
        return platform.machine()

    def os_version(self):
        """Return identifier to operating system version."""
        distribution, version, _ = platform.linux_distribution(
            full_distribution_name=False
        )
        return "{}=={}".format(distribution, version)


class MacOsPlatform(object):
    """Mac platform."""

    def name(self):
        """Return platform name."""
        return "mac"

    def arch(self):
        """Return architecture ("x86_64" or "i386")."""
        return platform.machine()

    def os_version(self):
        """Return identifier to operating system version."""
        return "{}=={}".format(self.name(), platform.mac_ver()[0])


class WindowsPlatform(object):
    """Windows platform."""

    def name(self):
        """Return platform name."""
        return "windows"

    def arch(self):
        """Return architecture ("x86_64" or "i386")."""
        # Work around this bug: https://bugs.python.org/issue7860
        if os.name == "nt" and sys.version_info[:2] < (2, 7):
            arch = os.environ.get(
                "PROCESSOR_ARCHITEW6432",
                os.environ.get("PROCESSOR_ARCHITECTURE")
            )
            if arch is not None:
                return arch

        return platform.machine()

    def os_version(self):
        """Return identifier to operating system version."""
        return "{}=={}".format(self.name(), platform.win32_ver()[1])
