#
# MARK: - Manage CMake Toolchain Files in a Directory
#

from __future__ import annotations
from pathlib import Path
import os
from .BuildSystemDescriptor import CMakeToolchain, BuildSystemIdentifier, HostSystem, Architecture
from .Utilities import remove_file_if_exist


class CMakeToolchainDirectory:
    def __init__(self, path: Path):
        """
        Initialize the directory with the path to the folder that stores CMake toolchain files
        :param path: Path to the folder that contains `.cmake` toolchain files
        """
        self.path = path

    def fetch_all(self) -> list[CMakeToolchain]:
        """
        Fetch all CMake toolchains in this directory, skipping files with malformed names
        :return: A list of parsed CMake toolchains. Order is unspecified.
        """
        results: list[CMakeToolchain] = []
        for file_path in self.path.glob("*.cmake"):
            try:
                results.append(CMakeToolchain.parse(file_path))
            except ValueError as error:
                print(f"[Warning] Skipping malformed CMake toolchain file at {file_path}: {error}", flush=True)
        return results

    def fetch_compatible(self, host_system: HostSystem, architecture: Architecture) -> list[CMakeToolchain]:
        """
        Fetch all CMake toolchains in this directory that are compatible with the given host system
        :param host_system: The host system on which the toolchain will be used
        :param architecture: The CPU architecture of the host system
        :return: A list of parsed CMake toolchains. Order is unspecified.
        """
        return [toolchain for toolchain in self.fetch_all() if toolchain.identifier.compatible(host_system, architecture)]

    def fetch_compatible_as_map(self, host_system: HostSystem, architecture: Architecture) -> dict[BuildSystemIdentifier, CMakeToolchain]:
        """
        Fetch all CMake toolchains in this directory compatible with the given host system, keyed by identifier
        :param host_system: The host system on which the toolchain will be used
        :param architecture: The CPU architecture of the host system
        :return: A map that associates each `BuildSystemIdentifier` with its `CMakeToolchain`.
        """
        return {toolchain.identifier: toolchain for toolchain in self.fetch_compatible(host_system, architecture)}

    def find(self, name: str) -> CMakeToolchain:
        """
        Find the CMake toolchain with the given name (without the `.cmake` extension)
        :param name: The stem of a CMake toolchain file (e.g., `x86-64_GCC-14_Ubuntu_APT`)
        :return: The parsed CMake toolchain.
        :raise FileNotFoundError: if no such toolchain file exists in this directory.
        :raise ValueError: if the file exists but its name cannot be parsed.
        """
        file_path = self.path / f"{name}.cmake"
        if not file_path.is_file():
            raise FileNotFoundError(f"CMake toolchain file '{name}.cmake' cannot be found in {self.path}.")
        return CMakeToolchain.parse(file_path)

    def select(self, toolchain: CMakeToolchain, as_link_at: Path) -> None:
        """
        Create a symlink at the given path pointing to the given CMake toolchain file
        :param toolchain: The CMake toolchain to be linked
        :param as_link_at: The absolute path at which the symlink should be created
        """
        remove_file_if_exist(as_link_at)
        os.symlink(self.path / toolchain.filename, as_link_at)
