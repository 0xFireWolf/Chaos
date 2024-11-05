#
# MARK: - Utilities
#
import shutil
import subprocess
import os
import sys
from pathlib import Path


def brew_install(packages: list[str]) -> None:
    """
    Use Homebrew to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    executable_path = Path(shutil.which("brew"))
    print(f"Found the Homebrew at {executable_path}.", flush=True)
    if not hasattr(brew_install, "updated"):
        subprocess.run([executable_path, "update"]).check_returncode()
        brew_install.updated = True
    subprocess.run([executable_path, "install"] + packages).check_returncode()


def apt_install(packages: list[str]) -> None:
    """
    Use APT to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["sudo", "apt", "update", "-y"])
    subprocess.run(["sudo", "apt", "-y", "install"] + packages).check_returncode()


def apt_add_repository(name: str) -> None:
    """
    Add an APT repository of the given name
    :param name: The repository name
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["sudo", "add-apt-repository", "-y", name]).check_returncode()


def pkg_install(packages: list[str]) -> None:
    """
    Use PKG to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["sudo", "pkg", "update"])
    subprocess.run(["sudo", "pkg", "install", "-y"] + packages).check_returncode()


def pip_install(packages: list[str]) -> None:
    """
    Use Pip to install the given list of Python package
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages).check_returncode()

def winget_install(packages: list[str]) -> None:
    """
    Use winget to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    for package in packages:
        if subprocess.run(["winget", "list", package], stdout=subprocess.DEVNULL).returncode != 0:
            subprocess.run(["winget", "install", package, "--scope", "machine"]).check_returncode()
        else:
            # Attempt to upgrade the package
            subprocess.run(["winget", "upgrade", package, "--scope", "machine"])


def choco_install(packages: list[str]) -> None:
    """
    Use Chocolatey to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    for package in packages:
        subprocess.run(["choco", "install", "-y", package]).check_returncode()


def powershell(command: str) -> None:
    """
    Run the given command in Powershell
    :param command: A Powershell command
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["powershell", "-Command", command]).check_returncode()


def remove_file_if_exist(file: Path) -> None:
    """
    Remove the given file if it exists
    :param file: The name of the file
    """
    if os.path.lexists(file):
        os.remove(file)


def remove_folder_if_exists(folder: Path) -> None:
    """
    Remove the given folder if it exists
    :param folder: The name of the folder
    """
    if os.path.exists(folder):
        shutil.rmtree(folder)


def is_conan_v2_installed() -> bool:
    """
    Check whether Conan 2.x instead of 1.x is installed on the local computer
    :return: `true` if Conan 2.x has been installed, `false` otherwise.
    """
    if not hasattr(is_conan_v2_installed, "result"):
        is_conan_v2_installed.result = subprocess.check_output(["conan", "--version"], text=True).startswith("Conan version 2")
    return is_conan_v2_installed.result


def powershell(command: str) -> None:
    """
    Run the given command in Powershell
    :param command: A powershell command
    """
    subprocess.run(["powershell", "-Command", command]).check_returncode()
