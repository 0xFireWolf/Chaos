#
# MARK: - Download and Manage CMake Binaries
#

from __future__ import annotations
from io import BytesIO
from pathlib import Path
from abc import ABC, abstractmethod
import re
import requests
import tarfile
import zipfile
from .CMake import CMake
from .Version import Version


# An abstract manager that downloads and manages CMake binaries for a specific operating system
class CMakeManager(ABC):
    # Default timeout (in seconds) for all HTTP requests
    kHTTPRequestTimeout = 30

    @staticmethod
    def _http_get(url: str) -> requests.Response:
        """
        [Helper] Fetch the content at the given URL with a sensible timeout and error handling
        :param url: The URL to fetch
        :return: The HTTP response.
        :raise requests.RequestException: if the request fails or returns a non-2xx status code.
        """
        response = requests.get(url, timeout=CMakeManager.kHTTPRequestTimeout)
        response.raise_for_status()
        return response

    @staticmethod
    def _parse_version_from_folder_name(folder_name: str) -> Version:
        """
        [Helper] Parse the CMake version from an extracted installer folder name
        :param folder_name: The folder name (e.g., `cmake-3.28.1-linux-x86_64`)
        :return: The parsed CMake version.
        :raise ValueError: if the folder name does not contain a recognizable version string.
        """
        match = re.search(r"cmake-(\d+\.\d+\.\d+)", folder_name)
        if match is None:
            raise ValueError(f"Cannot parse CMake version from folder name: {folder_name}")
        return Version.parse(match.group(1))

    def get_installer_filenames_with_patterns(self, major: int, minor: int, patterns: list[str]) -> list[str]:
        """
        [Helper] Get all CMake installers that have the given major and minor version
        :param major: The major version of CMake installers
        :param minor: The minor version of CMake installers
        :param patterns: A list of regular expressions used to find CMake installers for a specific operating system
        :return: A list of file names sorted in ascending order.
        """
        html = self._http_get(f"https://cmake.org/files/v{major}.{minor}/").text
        for pattern in patterns:
            files = list(re.findall(pattern, html))
            if len(files) != 0:
                return sorted(files)
        return []

    @abstractmethod
    def get_installer_filenames(self, major: int, minor: int) -> list[str]:
        """
        Get all CMake installers that have the given major and minor version for the current operating system
        :param major: The major version of CMake installers
        :param minor: The minor version of CMake installers
        :return: A list of file names sorted in ascending order.
        """
        raise NotImplementedError

    def get_installer_urls(self, major: int, minor: int) -> list[str]:
        """
        Get URLs of all CMake installers that have the given major and minor version for the current operating systems
        :param major: The major version of CMake installers
        :param minor: The minor version of CMake installers
        :return: A list of URLs sorted in ascending order.
        """
        return [f"https://cmake.org/files/v{major}.{minor}/{filename}"
                for filename in self.get_installer_filenames(major, minor)]

    def get_all_installer_versions(self, min_major: int, min_minor: int) -> list[tuple[int, int]]:
        """
        Get all CMake versions that are greater or equal to the given major and minor version
        :param min_major: The minimum major version of CMake installers
        :param min_minor: The minimum minor version of CMake installers
        :return: A list of versions, each of which is a pair of <major, minor> version.
        """
        print(f"Fetching all available CMake releases with major >= {min_major} and minor >= {min_minor}...")
        html = self._http_get("https://cmake.org/files/").text
        result = [(int(major), int(minor)) for (major, minor) in re.findall(r'href="v(\d+)\.(\d+)/"', html)]
        return sorted(list(filter(lambda pair: pair[0] >= min_major and pair[1] >= min_minor, result)))

    def get_all_installer_urls(self, min_major: int, min_minor: int) -> dict[tuple[int, int], list[str]]:
        """
        Get URLs of all CMake installers that are greater or equal to the given major and minor version
        :param min_major: The minimum major version of CMake installers
        :param min_minor: The minimum minor version of CMake installers
        :return: A map that associates each pair of <major, minor> version with a list of URLs to CMake installers.
        """
        return {(major, minor): self.get_installer_urls(major, minor)
                for major, minor in self.get_all_installer_versions(min_major, min_minor)}

    @abstractmethod
    def get_cmake_binary(self, from_url: str, to_directory: Path) -> CMake:
        """
        Download the CMake installer from the given URL, extract and store the CMake binary to the given directory
        :param from_url: URL to the CMake installer to be downloaded
        :param to_directory: Path to the directory to store the extracted CMake binary
        :return: A handle to the downloaded CMake binary.
        """
        raise NotImplementedError

    def get_cmake_binaries(self, min_major: int, min_minor: int, to_directory: Path,
                           latest_patch_only: bool = True) -> list[CMake]:
        """
        Download all CMake binaries that are greater or equal to the given major and minor version
        :param min_major: The minimum major version of CMake installers
        :param min_minor: The minimum minor version of CMake installers
        :param to_directory: Path to the directory to store the extracted CMake binary
        :param latest_patch_only: Pass `True` to only download the latest patch version for each release
        :return: A list of CMake binary descriptors.
        """
        binaries = list[CMake]()
        for (major, minor), urls in self.get_all_installer_urls(min_major, min_minor).items():
            print(f"Downloading CMake v{major}.{minor} Releases...")
            if latest_patch_only:
                urls = [urls[-1]]
            binaries.extend([self.get_cmake_binary(url, to_directory) for url in urls])
        return binaries


class CMakeManagerMacOS(CMakeManager):
    def get_installer_filenames(self, major: int, minor: int) -> list[str]:
        """
        Get all CMake installers that have the given major and minor version for macOS
        :param major: The major version of CMake installers
        :param minor: The minor version of CMake installers
        :return: A list of file names sorted in ascending order.
        """
        patterns = [r'href="(cmake-{}\.{}\.\d+-macos-universal\.tar\.gz)"'.format(major, minor),
                    r'href="(cmake-{}\.{}\.\d+-Darwin-x86_64\.tar\.gz)"'.format(major, minor),
                    r'href="(cmake-{}\.{}\.\d+-Darwin64-universal\.tar\.gz)"'.format(major, minor)]
        return self.get_installer_filenames_with_patterns(major, minor, patterns)

    def get_cmake_binary(self, from_url: str, to_directory: Path) -> CMake:
        """
        Download the CMake installer from the given URL, extract and store the CMake binary to the given directory
        :param from_url: URL to the CMake installer to be downloaded
        :param to_directory: Path to the directory to store the extracted CMake binary
        :return: A descriptor that describes the downloaded CMake binary.
        """
        folder_name = from_url.rsplit("/", 1)[-1].removesuffix(".tar.gz")
        versions = re.findall(r"cmake-(\d+)\.(\d+)\.(\d+)", folder_name)[0]
        executable_path = to_directory / folder_name / "CMake.app" / "Contents" / "bin" / "cmake"
        print(f"Downloading CMake v{versions[0]}.{versions[1]}.{versions[2]} for macOS...")
        with tarfile.open(fileobj=BytesIO(requests.get(from_url).content)) as archive:
            archive.extractall(path=to_directory)
        return CMake(int(versions[0]), int(versions[1]), int(versions[2]), executable_path)


class CMakeManagerLinux(CMakeManager):
    def get_installer_filenames(self, major: int, minor: int) -> list[str]:
        """
        Get all CMake installers that have the given major and minor version for Linux
        :param major: The major version of CMake installers
        :param minor: The minor version of CMake installers
        :return: A list of file names sorted in ascending order.
        """
        patterns = [r'href="(cmake-{}\.{}\.\d+-linux-x86_64\.tar\.gz)"'.format(major, minor),
                    r'href="(cmake-{}\.{}\.\d+-Linux-x86_64\.tar\.gz)"'.format(major, minor),
                    r'href="(cmake-{}\.{}\.\d+-Linux-i386\.tar\.gz)"'.format(major, minor)]
        return self.get_installer_filenames_with_patterns(major, minor, patterns)

    def get_cmake_binary(self, from_url: str, to_directory: Path) -> CMake:
        """
        Download the CMake installer from the given URL, extract and store the CMake binary to the given directory
        :param from_url: URL to the CMake installer to be downloaded
        :param to_directory: Path to the directory to store the extracted CMake binary
        :return: A descriptor that describes the downloaded CMake binary.
        """
        folder_name = from_url.rsplit("/", 1)[-1].removesuffix(".tar.gz")
        versions = re.findall(r"cmake-(\d+)\.(\d+)\.(\d+)", folder_name)[0]
        executable_path = to_directory / folder_name / "bin" / "cmake"
        print(f"Downloading CMake v{versions[0]}.{versions[1]}.{versions[2]} for Linux...")
        with tarfile.open(fileobj=BytesIO(requests.get(from_url).content)) as archive:
            archive.extractall(path=to_directory)
        return CMake(int(versions[0]), int(versions[1]), int(versions[2]), executable_path)


class CMakeManagerWindows(CMakeManager):
    def get_installer_filenames(self, major: int, minor: int) -> list[str]:
        """
        [Helper] Get all CMake installers that have the given major and minor version for Windows
        :param major: The major version of CMake installers
        :param minor: The minor version of CMake installers
        :return: A list of file names sorted in ascending order.
        """
        patterns = [r'href="(cmake-{}\.{}\.\d+-windows-x86_64.zip)"'.format(major, minor),
                    r'href="(cmake-{}\.{}\.\d+-win64-x64.zip)"'.format(major, minor),
                    r'href="(cmake-{}\.{}\.\d+-win32-x86.zip)"'.format(major, minor)]
        return self.get_installer_filenames_with_patterns(major, minor, patterns)

    def get_cmake_binary(self, from_url: str, to_directory: Path) -> CMake:
        """
        Download the CMake installer from the given URL, extract and store the CMake binary to the given directory
        :param from_url: URL to the CMake installer to be downloaded
        :param to_directory: Path to the directory to store the extracted CMake binary
        :return: A descriptor that describes the downloaded CMake binary.
        """
        folder_name = from_url.rsplit("/", 1)[-1].removesuffix(".zip")
        versions = re.findall(r"cmake-(\d+)\.(\d+)\.(\d+)", folder_name)[0]
        executable_path = to_directory / folder_name / "bin" / "cmake.exe"
        print(f"Downloading CMake v{versions[0]}.{versions[1]}.{versions[2]} for Windows...")
        with zipfile.ZipFile(BytesIO(requests.get(from_url).content)) as archive:
            archive.extractall(path=to_directory)
        return CMake(int(versions[0]), int(versions[1]), int(versions[2]), executable_path)
