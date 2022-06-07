#
# MARK: - Configure Development Environment
#

import os
import tempfile
import shutil
from .Utilities import *


# An abstract configurator that sets up the development environment on the host system
class EnvironmentConfigurator:
    def install_build_essentials(self) -> None:
        raise NotImplementedError

    def install_cmake(self) -> None:
        raise NotImplementedError

    def install_conan(self) -> None:
        raise NotImplementedError

    def install_other(self) -> None:
        pass

    def install_all(self) -> None:
        self.install_build_essentials()
        self.install_cmake()
        self.install_conan()
        self.install_other()


# A configurator that sets up the development environment on macOS
class EnvironmentConfiguratorMacOS(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        subprocess.run(["sudo", "xcode-select", "--install"])
        path = tempfile.mkdtemp()
        subprocess.run(["curl", "-O", "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"], cwd=path).check_returncode()
        os.chmod(path + "/install.sh", 0o755)
        subprocess.run([path + "/install.sh"]).check_returncode()
        shutil.rmtree(path)

    def install_cmake(self) -> None:
        brew_install(["cmake"])

    def install_conan(self) -> None:
        brew_install(["conan"])


# A configurator that sets up the development environment on Ubuntu 20.04 LTS / Ubuntu 22.04 LTS
class EnvironmentConfiguratorUbuntu(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        apt_install(["build-essential", "vim"])

    def install_cmake(self) -> None:
        apt_install(["cmake"])

    def install_conan(self) -> None:
        apt_install(["python3-pip"])
        pip_install(["conan"])
        subprocess.run(["sudo", "ln", "-s", os.path.expanduser("~") + "/.local/bin/conan", "/usr/local/bin/conan"]).check_returncode()


# A configurator that sets up the development environment on Windows 10 or later
class EnvironmentConfiguratorWindows(EnvironmentConfigurator):
    def install_build_essentials(self) -> None:
        pass

    def install_cmake(self) -> None:
        winget_install(["Kitware.CMake"])

    def install_conan(self) -> None:
        winget_install(["JFrog.Conan"])
