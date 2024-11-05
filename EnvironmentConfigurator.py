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
    def install_conan(self) -> None:
        raise NotImplementedError

    # def install_homebrew(self) -> None:
    #     # Check whether Homebrew has already been installed
    #     try:
    #         version = subprocess.check_output(["brew", "--version"], text=True).strip()
    #         print(f"{version} has already been installed.")
    #     except FileNotFoundError:
    #         print("Homebrew is not installed. Installing...")
    #         subprocess.run(["sudo", "xcode-select", "--install"])
    #         path = tempfile.mkdtemp()
    #         subprocess.run(["curl", "-O", "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"],
    #                        cwd=path).check_returncode()
    #         os.chmod(path + "/install.sh", 0o755)
    #         subprocess.run([path + "/install.sh"]).check_returncode()
    #         shutil.rmtree(path)

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


# A configurator that sets up the development environment on macOS
class EnvironmentConfiguratorMacOS(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        brew_install(["wget"])

    def install_cmake(self) -> None:
        brew_install(["cmake"])

    def install_conan(self) -> None:
        pip_install(["conan"])


# A configurator that sets up the development environment on Ubuntu 20.04 LTS / Ubuntu 22.04 LTS
class EnvironmentConfiguratorUbuntu(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        apt_install(["build-essential", "vim"])

    def install_cmake(self) -> None:
        apt_install(["cmake"])

    def install_conan(self) -> None:
        apt_install(["python3-pip"])
        pip_install(["conan"])
        subprocess.run(["sudo", "rm", "-rf", "/usr/local/bin/conan"])
        subprocess.run(["sudo", "ln", "-s", os.path.expanduser("~") + "/.local/bin/conan", "/usr/local/bin/conan"]).check_returncode()


# A configurator that sets up the development environment on Windows 10 or later
class EnvironmentConfiguratorWindows(EnvironmentConfigurator):
    def install_winget(self) -> None:
        print("Installing the Windows Package Manager...")
        commands = [
        "$progressPreference = 'silentlyContinue'",
        "Invoke-WebRequest -Uri https://aka.ms/getwinget -OutFile Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle",
        "Invoke-WebRequest -Uri https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx -OutFile Microsoft.VCLibs.x64.14.00.Desktop.appx",
        "Invoke-WebRequest -Uri https://github.com/microsoft/microsoft-ui-xaml/releases/download/v2.8.6/Microsoft.UI.Xaml.2.8.x64.appx -OutFile Microsoft.UI.Xaml.2.8.x64.appx",
        "Add-AppxPackage Microsoft.VCLibs.x64.14.00.Desktop.appx",
        "Add-AppxPackage Microsoft.UI.Xaml.2.8.x64.appx",
        "Add-AppxPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle"
        ]
        for command in commands:
            powershell(command)
        print("Windows Package Manager has been installed.")

    def install_build_essentials(self) -> None:
        winget_path = shutil.which("winget")
        if winget_path is None:
            self.install_winget()
        else:
            print(f"Found winget at {winget_path}.")
        winget_install(["Git.Git"])

    def install_cmake(self) -> None:
        winget_install(["Kitware.CMake"])

    def install_conan(self) -> None:
        winget_install(["JFrog.Conan"])


# A configurator that sets up the development environment on FreeBSD
class EnvironmentConfiguratorFreeBSD(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        pass

    def install_cmake(self) -> None:
        pkg_install(["cmake"])

    def install_conan(self) -> None:
        pkg_install(["py311-sqlite3"])
        pip_install(["conan"])
