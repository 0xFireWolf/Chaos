#
# MARK: - Configure Development Environment
#

import tempfile
from abc import ABC, abstractmethod
from typing import Callable
from .Utilities import *


# An abstract configurator that sets up the development environment on the host system
class EnvironmentConfigurator(ABC):
    def __init__(self, installer: Callable[[], None] = None):
        self.other_tools_installer = installer

    @abstractmethod
    def install_build_essentials(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_cmake(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_ninja(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_conan(self) -> None:
        raise NotImplementedError

    def install_other(self) -> None:
        if self.other_tools_installer is not None:
            print("Installing additional required development tools...")
            self.other_tools_installer()
        else:
            print("This project does not require any additional development tools.")

    def install_basic(self) -> None:
        self.install_build_essentials()
        self.install_cmake()
        self.install_ninja()
        self.install_conan()

    def install_all(self) -> None:
        self.install_basic()
        self.install_other()


# A configurator that sets up the development environment on macOS
class EnvironmentConfiguratorMacOS(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        # Check whether Homebrew has already been installed
        try:
            version = subprocess.check_output(["brew", "--version"], text=True).strip()
            print(f"{version} has already been installed.")
        except FileNotFoundError:
            print("Homebrew is not installed. Installing...")
            subprocess.run(["sudo", "xcode-select", "--install"])
            path = tempfile.mkdtemp()
            subprocess.run(["curl", "-O", "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"], cwd=path).check_returncode()
            os.chmod(path + "/install.sh", 0o755)
            subprocess.run([path + "/install.sh"]).check_returncode()
            shutil.rmtree(path)

    def install_cmake(self) -> None:
        brew_install(["cmake"])

    def install_ninja(self) -> None:
        brew_install(["ninja"])

    def install_conan(self) -> None:
        pip_install(["conan"])


# A configurator that sets up the development environment on Ubuntu 20.04 LTS / Ubuntu 22.04 LTS
class EnvironmentConfiguratorUbuntu(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        apt_install(["build-essential", "vim"])

    def install_cmake(self) -> None:
        apt_install(["cmake"])

    def install_ninja(self) -> None:
        apt_install(["ninja-build"])

    def install_conan(self) -> None:
        apt_install(["python3-pip"])
        pip_install(["conan"])
        subprocess.run(["sudo", "rm", "-rf", "/usr/local/bin/conan"])
        subprocess.run(["sudo", "ln", "-s", os.path.expanduser("~") + "/.local/bin/conan", "/usr/local/bin/conan"]).check_returncode()


# A configurator that sets up the development environment on Windows 10 or later
class EnvironmentConfiguratorWindows(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        # Install Chocolatey
        powershell("Set-ExecutionPolicy Bypass -Scope Process -Force; "
                   "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
                   "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))")
        winget_install(["Git.Git"])

    def install_cmake(self) -> None:
        winget_install(["Kitware.CMake"])

    def install_ninja(self) -> None:
        choco_install(["ninja"])

    def install_conan(self) -> None:
        winget_install(["JFrog.Conan"])


# A configurator that sets up the development environment on FreeBSD
class EnvironmentConfiguratorFreeBSD(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        pass

    def install_cmake(self) -> None:
        pkg_install(["cmake"])

    def install_ninja(self) -> None:
        pkg_install(["ninja"])

    def install_conan(self) -> None:
        pkg_install(["py311-sqlite3"])
        pip_install(["conan"])
