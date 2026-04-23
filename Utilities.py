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
    brew = shutil.which("brew")
    if brew is None:
        raise FileNotFoundError("Homebrew is not installed or not on PATH.")
    executable_path = Path(brew)
    print(f"Found the Homebrew at {executable_path}.", flush=True)
    if not hasattr(brew_install, "updated"):
        if subprocess.run([executable_path, "update"]).returncode != 0:
            print("Warning: Unable to refresh the Homebrew package index.", flush=True)
        brew_install.updated = True
    subprocess.run([executable_path, "install"] + packages, check=True)


def apt_install(packages: list[str]) -> None:
    """
    Use APT to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    if subprocess.run(["sudo", "apt-get", "update", "-y"]).returncode != 0:
        print("Warning: Unable to refresh the package index files.", flush=True)
    subprocess.run(["sudo", "apt-get", "-y", "install"] + packages, check=True)


def apt_add_repository(name: str) -> None:
    """
    Add an APT repository of the given name
    :param name: The repository name
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["sudo", "add-apt-repository", "-y", name], check=True)


def pkg_install(packages: list[str]) -> None:
    """
    Use PKG to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    if subprocess.run(["sudo", "pkg", "update"]).returncode != 0:
        print("Warning: Unable to refresh the package index files.", flush=True)
    subprocess.run(["sudo", "pkg", "install", "-y"] + packages, check=True)


def pip_install(packages: list[str]) -> None:
    """
    Use Pip to install the given list of Python package
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages, check=True)


def winget_install(packages: list[str]) -> None:
    """
    Use winget to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    for package in packages:
        if subprocess.run(["winget", "list",
                           "--id", package, "--exact",
                           "--accept-source-agreements"],
                          stdout=subprocess.DEVNULL).returncode != 0:
            subprocess.run(["winget", "install",
                            "--id", package, "--exact",
                            "--scope", "machine",
                            "--accept-source-agreements",
                            "--accept-package-agreements"], check=True)
        else:
            # Attempt to upgrade the package
            if subprocess.run(["winget", "upgrade",
                               "--id", package, "--exact",
                               "--scope", "machine",
                               "--accept-source-agreements", 
                               "--accept-package-agreements"]).returncode != 0:
                print(f"Warning: Failed to upgrade the package {package}.", flush=True)


def choco_install(packages: list[str]) -> None:
    """
    Use Chocolatey to install the given list of packages
    :param packages: Name of the packages
    :raise `CalledProcessError` on error.
    """
    for package in packages:
        subprocess.run(["choco", "install", "-y", package], check=True)


def powershell(command: str, cwd: Path | None = None) -> None:
    """
    Run the given command in PowerShell
    :param command: A PowerShell command
    :param cwd: The working directory
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["PowerShell", "-Command", command], cwd=cwd, check=True)


def remove_file_if_exists(file: Path) -> None:
    """
    Remove the given file if it exists
    :param file: The name of the file
    """
    file.unlink(missing_ok=True)


def remove_folder_if_exists(folder: Path) -> None:
    """
    Remove the given folder if it exists
    :param folder: The name of the folder
    """
    try:
        shutil.rmtree(folder)
    except FileNotFoundError:
        pass
