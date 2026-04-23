#
# MARK: - Configure Development Environment
#

import tempfile
import subprocess
import shutil
import sys
from abc import ABC, abstractmethod
from typing import Callable
from pathlib import Path

import requests

from .Conan import Conan
from .Utilities import (
    apt_install,
    brew_install,
    pip_install,
    pkg_install,
    powershell,
    winget_install,
)


# An abstract configurator that sets up the development environment on the host system
class EnvironmentConfigurator(ABC):
    def __init__(self, installer: Callable[[], None] | None = None):
        self.other_tools_installer = installer

    @abstractmethod
    def install_build_essentials(self) -> None:
        pass

    @abstractmethod
    def install_cmake(self) -> None:
        pass

    @abstractmethod
    def install_conan(self) -> None:
        pass

    def install_other(self) -> None:
        if self.other_tools_installer is not None:
            print("Installing additional required development tools...")
            self.other_tools_installer()
        else:
            print("This project does not require any additional development tools.")

    def install_basic(self) -> None:
        self.install_build_essentials()
        self.install_cmake()
        self.install_conan()

    def install_all(self) -> None:
        self.install_basic()
        self.install_other()

    def ensure_conancenter_url(self) -> None:
        Conan.default().ensure_conan_remote("conancenter", "https://center2.conan.io")


# A configurator that sets up the development environment on macOS
class EnvironmentConfiguratorMacOS(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        brew_install(["wget"])

    def install_cmake(self) -> None:
        brew_install(["cmake"])

    def install_conan(self) -> None:
        pip_install(["conan"])
        self.ensure_conancenter_url()


# A configurator that sets up the development environment on Ubuntu
class EnvironmentConfiguratorUbuntu(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        apt_install(["build-essential", "vim"])

    def install_cmake(self) -> None:
        apt_install(["cmake"])

    def install_conan(self) -> None:
        apt_install(["python3-pip"])
        pip_install(["conan"])
        conan_user_path = Path.home() / ".local" / "bin" / "conan"
        subprocess.run(["sudo", "rm", "-f", "/usr/local/bin/conan"], check=True)
        subprocess.run(["sudo", "ln", "-s", str(conan_user_path), "/usr/local/bin/conan"], check=True)
        self.ensure_conancenter_url()


# A configurator that sets up the development environment on Windows 10 or later
class EnvironmentConfiguratorWindows(EnvironmentConfigurator):
    def install_winget(self) -> None:
        # TODO: DEPRECATED, This is fragile
        print("Installing the Windows Package Manager...")
        with tempfile.TemporaryDirectory() as temp_dir:
            uris = ["https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx",
                    "https://github.com/microsoft/microsoft-ui-xaml/releases/download/v2.8.6/Microsoft.UI.Xaml.2.8.x64.appx",
                    "https://aka.ms/getwinget"]
            filenames = ["Microsoft.VCLibs.x64.14.00.Desktop.appx",
                         "Microsoft.UI.Xaml.2.8.x64.appx",
                         "Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle"]
            for (uri, filename) in zip(uris, filenames):
                print(f"Downloading {filename}...")
                full_path = Path(temp_dir) / filename
                response = requests.get(uri, timeout=30)
                response.raise_for_status()
                with open(full_path, "wb") as file:
                    file.write(response.content)
                print(f"Installing {filename}...")
                powershell(f'Add-AppxPackage "{full_path}"')
                print(f"{filename} has been installed.")

    def install_build_essentials(self) -> None:
        # winget_path = shutil.which("winget")
        # if winget_path is None:
        #     self.install_winget()
        # else:
        #     print(f"Found winget at {winget_path}.")
        winget_install(["Git.Git"])

    def install_cmake(self) -> None:
        winget_install(["Kitware.CMake"])

    def install_conan(self) -> None:
        pip_install(["conan"])
        self.ensure_conancenter_url()


# A configurator that sets up the development environment on FreeBSD
class EnvironmentConfiguratorFreeBSD(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        print("FreeBSD ships with a base toolchain; no build essentials to install.")

    def install_cmake(self) -> None:
        pkg_install(["cmake"])

    def install_conan(self) -> None:
        major_minor = f"{sys.version_info.major}{sys.version_info.minor}"
        pkg_install([f"py{major_minor}-sqlite3"])
        pip_install(["conan"])
        self.ensure_conancenter_url()
