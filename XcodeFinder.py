import os
import re
import plistlib
import subprocess
from pathlib import Path
from .Version import Version


kCFBundleIdentifier = "CFBundleIdentifier"
kCFBundleShortVersionString = "CFBundleShortVersionString"


class XcodeBundle:
    def __init__(self, path: Path):
        """
        Attempt to parse an Xcode bundle at the given path
        :param path: The path to an Xcode bundle (e.g., `/Applications/Xcode.app`)
        :raise `KeyError` if one of the required `CFBundle` properties is missing in `Info.plist`.
               `ValueError` if the required `CFBundle` properties do not match the one of `Xcode`.
        """
        with open(path / "Contents" / "Info.plist", "rb") as info:
            plist = plistlib.load(info)
            if plist[kCFBundleIdentifier] != "com.apple.dt.Xcode":
                raise ValueError("Mismatched bundle identifier.")
            self.path = path
            self.version = Version.parse(plist[kCFBundleShortVersionString])

    @property
    def developer_directory(self) -> Path:
        """
        Get the path to the developer directory
        :return: The path to the developer directory that can be recognized by `xcode-select`.
        """
        return self.path / "Contents" / "Developer"

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
        return f"{self.path}\n\tVersion: {self.version}"


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

    def find_all_as_map(self) -> dict[Version, XcodeBundle]:
        """
        Find all Xcode bundles and return them as a map keyed by version
        :return: A map that associates each version with its corresponding Xcode bundle.
        """
        return {bundle.version: bundle for bundle in self.find_all()}

    def find(self, version: Version) -> XcodeBundle | None:
        """
        Find the Xcode bundle of the given version
        :param version: The version of the Xcode bundle to find
        :return: The Xcode bundle of the given version on success, `None` otherwise.
        """
        for bundle in self.find_all():
            if bundle.version == version:
                return bundle
        return None
