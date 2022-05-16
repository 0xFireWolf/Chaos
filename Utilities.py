#
# MARK: - Utilities
#

import subprocess


def brew_install(packages: list[str]) -> None:
    """
    Use Homebrew to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["brew", "install"] + packages).check_returncode()


def apt_install(packages: list[str]) -> None:
    """
    Use APT to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
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
    :param packages:  Name of the packages
    :raise `CalledProcessError` on error.
    """
    for package in packages:
        subprocess.run(["winget", "install", package]).check_returncode()
