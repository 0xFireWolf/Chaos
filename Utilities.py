#
# MARK: - Utilities
#

import subprocess


def brew_install(packages: list[str]) -> None:
    subprocess.run(["brew", "install"] + packages)


def apt_install(packages: list[str]) -> None:
    subprocess.run(["sudo", "apt", "-y", "install"] + packages)


def apt_add_repository(name: str) -> None:
    subprocess.run(["sudo", "add-apt-repository", "-y", name])


def pip_install(packages: list[str]) -> None:
    subprocess.run(["sudo", "pip", "install"] + packages)


def winget_install(packages: list[str]) -> None:
    for package in packages:
        subprocess.run(["winget", "install", package])