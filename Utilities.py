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


def powershell(command: str, cwd: Path = Path.cwd()) -> None:
    """
    Run the given command in PowerShell
    :param command: A PowerShell command
    :param cwd: The working directory
    :raise `CalledProcessError` on error.
    """
    subprocess.run(["PowerShell", "-Command", command], cwd=cwd).check_returncode()


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
    if os.path.lexists(folder):
        shutil.rmtree(folder)
