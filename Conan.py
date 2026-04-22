#
# MARK: - A helper class that can be used to invoke `conan`
#

from __future__ import annotations
from pathlib import Path
from functools import cache
import re
import shutil
import subprocess
from .Version import Version


class Conan:
    def __init__(self, path: Path, version: Version):
        """
        Initialize a Conan handle from the path to the binary and its version
        :param path: The absolute path to the `conan` executable
        :param version: The version of the `conan` executable
        """
        self.path = path
        self.version = version

    @classmethod
    @cache
    def default(cls) -> Conan:
        """
        Get a handle to the default `conan` binary resolved via the current shell environment
        :return: A handle to the default `conan` binary.
        :raise RuntimeError: if `conan` cannot be found on `PATH` or if its version is not 2.x.
        """
        resolved = shutil.which("conan")
        if resolved is None:
            raise RuntimeError("Cannot find `conan` on PATH. "
                               "Please install Conan 2.x or verify your PATH environment variable.")
        path = Path(resolved)
        output = subprocess.check_output([path, "--version"], text=True)
        match = re.search(r"Conan version (\d+\.\d+\.\d+)", output)
        if match is None:
            raise RuntimeError(f"Failed to parse the version of `conan` from its output: {output}")
        version = Version.parse(match.group(1))
        if version.major != 2:
            raise RuntimeError(f"Conan v{version} is not supported. Please install Conan 2.x.")
        print(f"Found the default Conan v{version} at {path}.")
        return cls(path, version)

    #
    # MARK: Constants
    #

    @property
    def integration_file_name(self) -> str:
        """
        Get the name of the Conan-generated CMake integration file
        :return: The name of the integration file that can be chain loaded by a CMake toolchain file.
        """
        return "conan_toolchain.cmake"

    #
    # MARK: Invoke `conan`
    #

    def _run(self, args: list[str | Path]) -> None:
        """
        [Helper] Invoke `conan` with the given list of arguments
        :param args: A list of arguments passed to the `conan` binary
        :raise `CalledProcessError` if `conan` exits with a non-zero status code.
        """
        full_args: list[str | Path] = [self.path] + args
        print(f"Conan v{self.version} Args: {' '.join(str(arg) for arg in full_args)}", flush=True)
        subprocess.run(full_args).check_returncode()

    #
    # MARK: Public Interface
    #

    def install(self, *,
                source_directory: Path,
                output_directory: Path,
                build_profile: Path,
                host_profile: Path,
                extra_args: list[str] = None) -> None:
        """
        Invoke `conan install` to install all required dependencies for the project
        :param source_directory: Path to the source directory in which `conanfile.txt` or `conanfile.py` resides
        :param output_directory: Path to the output directory in which generated files will be stored
        :param build_profile: Path to the Conan profile that specifies the build environment
        :param host_profile: Path to the Conan profile that specifies the host environment
        :param extra_args: Optional additional arguments passed to `conan install`
        :raise `CalledProcessError` if `conan` exits with a non-zero status code.
        """
        print(f"Installing all required dependencies using Conan v{self.version}...")
        args: list[str | Path] = ["install", source_directory,
                                  "--output-folder", output_directory,
                                  "--update",
                                  "--build", "missing",
                                  "--profile:build", build_profile,
                                  "--profile:host", host_profile]
        if extra_args is not None:
            args.extend(extra_args)
        self._run(args)

    def remove_all(self) -> None:
        """
        Invoke `conan remove` to remove all packages from Conan's local cache
        :raise `CalledProcessError` if `conan` exits with a non-zero status code.
        """
        print(f"Removing all packages from Conan's local cache using Conan v{self.version}...")
        self._run(["remove", "-c", "*"])
