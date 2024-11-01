import os
import re
import plistlib
import subprocess
from pathlib import Path
from operator import attrgetter


kCFBundleIdentifier = "CFBundleIdentifier"
kCFBundleShortVersionString = "CFBundleShortVersionString"


class XcodeBundle:
    def __init__(self, url: Path):
        """
        Attempt to parse an Xcode bundle at the given path
        :param url: The path to an Xcode bundle (e.g., `/Applications/Xcode.app`)
        :raise `KeyError` if one of the required `CFBundle` properties is missing in `Info.plist`.
               `ValueError` if the required `CFBundle` properties do not match the one of `Xcode`.
        """
        with open(url / "Contents" / "Info.plist", "rb") as info:
            plist = plistlib.load(info)
            if plist[kCFBundleIdentifier] != "com.apple.dt.Xcode":
                raise ValueError("Mismatched bundle identifier.")
            tokens: list[str] = plist[kCFBundleShortVersionString].split(".")
            if len(tokens) != 2 and len(tokens) != 3:
                raise ValueError("Invalid bundle version.")
            self.url = url
            self.major = int(tokens[0])
            self.minor = int(tokens[1])
            self.patch = int(tokens[2]) if len(tokens) == 3 else 0

    @property
    def version(self) -> str:
        """
        Get the bundle version
        :return: The version string.
        """
        return "{}.{}.{}".format(self.major, self.minor, self.patch)

    @property
    def developer_directory(self) -> Path:
        """
        Get the path to the developer directory
        :return: The path to the developer directory that can be recognized by `xcode-select`.
        """
        return self.url / "Contents" / "Developer"

    def activate(self) -> None:
        """
        Activate the toolchain provided by this Xcode installation
        :raise `CalledProcessError` if failed to activate the toolchain via `xcode-select`.
        """
        subprocess.run(["sudo", "xcode-select", "--switch", self.developer_directory]).check_returncode()

    def __str__(self) -> str:
        """
        Get the string representation of this Xcode installation
        :return: A user-friendly string.
        """
        return "{}\n\tVersion: {}".format(self.url, self.version)


class XcodeFinder:
    def __init__(self, directories: list[Path], pattern: str):
        """
        Initialize the Xcode finder
        :param directories: A list of directory in which to search for Xcode installations
        :param pattern: A regular expression to filter out non-Xcode bundles to speed up the search process
        """
        self.directories = directories
        self.pattern = re.compile(pattern)

    def find_all_in_directory(self, directory: Path) -> list[XcodeBundle]:
        """
        Find all Xcode bundles in the given directory
        :param directory: A path to a directory in which to search for Xcode installations
        :return: A list of found Xcode bundles
        """
        bundles = list[XcodeBundle]()
        names: list[str] = os.listdir(directory)
        for name in names:
            if self.pattern.search(name):
                try:
                    bundles.append(XcodeBundle(directory / name))
                except (KeyError, ValueError):
                    continue
        return bundles

    def find_all(self) -> list[XcodeBundle]:
        """
        Find all Xcode bundles in each previously specified directory
        :return: A list of found Xcode bundles.
        """
        return [bundle for directory in self.directories for bundle in self.find_all_in_directory(directory)]

    def find(self, major: int, minor: int = None, patch: int = None) -> XcodeBundle:
        """
        Find the Xcode bundle of a specific version
        :param major: The major version
        :param minor: An optional minor version (Pass `None` to find the latest minor release)
        :param patch: An optional patch version (Pass `None` to find the latest patch release)
        :return: The Xcode bundle of the given version on success, `None` otherwise.
        """
        bundles = [bundle for bundle in self.find_all() if bundle.major == major]
        if minor is None:
            bundles = sorted(bundles, key=attrgetter("minor"), reverse=True)
        else:
            bundles = [bundle for bundle in bundles if bundle.minor == minor]
            if patch is None:
                bundles = sorted(bundles, key=attrgetter("patch"), reverse=True)
            else:
                bundles = [bundle for bundle in bundles if bundle.patch == patch]
        return bundles[0] if len(bundles) != 0 else None
