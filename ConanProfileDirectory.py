#
# MARK: - Manage Conan Profiles in a Directory
#

from __future__ import annotations
from pathlib import Path
import os
from .BuildSystemDescriptor import ConanProfile, ConanProfilePair, BuildSystemIdentifier, BuildType, HostSystem, Architecture
from .Utilities import remove_file_if_exist


class ConanProfileDirectory:
    def __init__(self, path: Path):
        """
        Initialize the directory with the path to the folder that stores Conan profiles
        :param path: Path to the folder that contains `.conanprofile` files
        """
        self.path = path

    def fetch_all(self) -> list[ConanProfile]:
        """
        Fetch all Conan profiles in this directory, skipping files with malformed names
        :return: A list of parsed Conan profiles. Order is unspecified.
        """
        results: list[ConanProfile] = []
        for file_path in self.path.glob("*.conanprofile"):
            try:
                results.append(ConanProfile.parse(file_path))
            except ValueError as error:
                print(f"[Warning] Skipping malformed Conan profile at {file_path}: {error}", flush=True)
        return results

    def fetch_compatible(self, host_system: HostSystem, architecture: Architecture) -> list[ConanProfile]:
        """
        Fetch all Conan profiles compatible with the given host system
        :param host_system: The host system on which the profile will be used
        :param architecture: The CPU architecture of the host system
        :return: A list of parsed Conan profiles. Order is unspecified.
        """
        return [profile for profile in self.fetch_all() if profile.identifier.compatible(host_system, architecture)]

    def fetch_compatible_as_map(self, host_system: HostSystem, architecture: Architecture) -> dict[BuildSystemIdentifier, ConanProfilePair]:
        """
        Fetch all Conan profiles compatible with the given host system, paired by build type and keyed by identifier

        Identifiers without both a Debug and a Release profile are skipped with a warning.
        :param host_system: The host system on which the profile will be used
        :param architecture: The CPU architecture of the host system
        :return: A map that associates each `BuildSystemIdentifier` with its complete `ConanProfilePair`.
        """
        debug_profiles: dict[BuildSystemIdentifier, ConanProfile] = {}
        release_profiles: dict[BuildSystemIdentifier, ConanProfile] = {}
        for profile in self.fetch_compatible(host_system, architecture):
            bucket = debug_profiles if profile.build_type == BuildType.kDebug else release_profiles
            bucket[profile.identifier] = profile

        pairs: dict[BuildSystemIdentifier, ConanProfilePair] = {}
        for identifier in debug_profiles.keys() | release_profiles.keys():
            debug = debug_profiles.get(identifier)
            release = release_profiles.get(identifier)
            if debug is None:
                print(f"[Warning] No Debug Conan profile for '{identifier}'; skipping.", flush=True)
                continue
            if release is None:
                print(f"[Warning] No Release Conan profile for '{identifier}'; skipping.", flush=True)
                continue
            pairs[identifier] = ConanProfilePair(debug=debug, release=release)
        return pairs

    def find(self, name: str) -> ConanProfilePair:
        """
        Find the Conan profile pair with the given name
        :param name: The stem of a Conan profile file, excluding the build-type suffix
                     (e.g., `x86-64_GCC-14_Ubuntu_APT`)
        :return: The parsed Conan profile pair.
        :raise FileNotFoundError: if either the Debug or Release profile is missing.
        :raise ValueError: if either file exists but its name cannot be parsed.
        """
        debug_path = self.path / f"{name}_{BuildType.kDebug.value}.conanprofile"
        release_path = self.path / f"{name}_{BuildType.kRelease.value}.conanprofile"
        if not debug_path.is_file():
            raise FileNotFoundError(f"Conan profile '{debug_path.name}' cannot be found in {self.path}.")
        if not release_path.is_file():
            raise FileNotFoundError(f"Conan profile '{release_path.name}' cannot be found in {self.path}.")
        return ConanProfilePair(debug=ConanProfile.parse(debug_path), release=ConanProfile.parse(release_path))

    def select(self, profile: ConanProfile, as_link_at: Path) -> None:
        """
        Create a symlink at the given path pointing to the given Conan profile
        :param profile: The Conan profile to be linked
        :param as_link_at: The absolute path at which the symlink should be created
        """
        remove_file_if_exist(as_link_at)
        os.symlink(self.path / profile.filename, as_link_at)
