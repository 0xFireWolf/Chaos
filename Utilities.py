#
# MARK: - Utilities
#
import shutil
import subprocess
import os


def brew_install(packages: list[str]) -> None:
    """
    Use Homebrew to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["brew", "update"]).check_returncode()
    subprocess.run(["brew", "install"] + packages).check_returncode()


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
    :param name: Name of the repository
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["sudo", "add-apt-repository", "-y", name]).check_returncode()


def pip_install(packages: list[str]) -> None:
    """
    Use Pip to install the given list of Python package
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["sudo", "pip", "install"] + packages).check_returncode()


def winget_install(packages: list[str]) -> None:
    """
    Use winget to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    for package in packages:
        subprocess.run(["winget", "install", package]).check_returncode()


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


def remove_file_if_exist(file: str) -> None:
    """
    Remove the given file if it exists
    :param file: The name of the file
    """
    if os.path.exists(file):
        os.remove(file)


def remove_folder_if_exists(folder: str) -> None:
    """
    Remove the given folder if it exists
    :param folder: The name of the folder
    """
    if os.path.exists(folder):
        shutil.rmtree(folder)
