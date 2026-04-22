#
# MARK: - A helper class that can be used to invoke `cmake`
#

from __future__ import annotations
from pathlib import Path
from functools import cache
import re
import shutil
import subprocess
from .BuildSystemDescriptor import BuildType
from .Version import Version


class CMake:
    def __init__(self, path: Path, version: Version):
        """
        Initialize a CMake handle from the path to the binary and its version
        :param path: The absolute path to the `cmake` executable
        :param version: The version of the `cmake` executable
        """
        self.path = path
        self.version = version

    @classmethod
    @cache
    def default(cls) -> CMake:
        """
        Get a handle to the default `cmake` binary resolved via the current shell environment
        :return: A handle to the default `cmake` binary.
        :raise RuntimeError: if `cmake` cannot be found on `PATH`.
        """
        resolved = shutil.which("cmake")
        if resolved is None:
            raise RuntimeError("Cannot find `cmake` on PATH. "
                               "Please install CMake or verify your PATH environment variable.")
        path = Path(resolved)
        output = subprocess.check_output([path, "--version"], text=True)
        match = re.search(r"cmake version (\d+\.\d+\.\d+)", output)
        if match is None:
            raise RuntimeError(f"Failed to parse the version of `cmake` from its output: {output}")
        version = Version.parse(match.group(1))
        print(f"Found the default CMake v{version} at {path}.")
        return cls(path, version)

    #
    # MARK: Invoke `cmake`
    #

    def _run(self, args: list[str | Path]) -> None:
        """
        [Helper] Invoke `cmake` with the given list of arguments
        :param args: A list of arguments passed to the `cmake` binary
        :raise CalledProcessError: if `cmake` exits with a non-zero status code.
        """
        full_args: list[str | Path] = [self.path] + args
        print(f"CMake v{self.version} Args: {' '.join(str(arg) for arg in full_args)}", flush=True)
        subprocess.run(full_args).check_returncode()

    #
    # MARK: Public Interface
    #

    @staticmethod
    def format_defines(defines: dict[str, str]) -> list[str]:
        """
        [Helper] Convert a dictionary of CMake cache variables to a list of `-D<KEY>=<VALUE>` arguments
        :param defines: A dictionary that maps each CMake cache variable name to its value
        :return: A list of `-D<KEY>=<VALUE>` arguments that can be passed to `cmake`.
        """
        return [f"-D{key}={value}" for key, value in defines.items()]

    def generate(self, *,
                 source_directory: Path,
                 build_directory: Path,
                 build_type: BuildType,
                 toolchain_file: Path = None,
                 chainload_toolchain_file: Path = None,
                 defines: dict[str, str] = None,
                 extra_args: list[str] = None) -> None:
        """
        Invoke `cmake` to generate files for the native build system
        :param source_directory: Path to the source directory in which `CMakeLists.txt` resides
        :param build_directory: Path to the build directory in which files for the native build system will be stored
        :param build_type: The build type (i.e., `Debug` or `Release`)
        :param toolchain_file: Optional path to the primary CMake toolchain file
        :param chainload_toolchain_file: Optional path to the secondary CMake toolchain file chain loaded by the primary
        :param defines: Optional additional CMake cache variables passed as `-D<KEY>=<VALUE>` arguments
        :param extra_args: Optional additional arguments passed to `cmake`
        :raise `CalledProcessError` if `cmake` exits with a non-zero status code.
        """
        print(f"Generating files for the native build system using CMake v{self.version}...")
        print(f"\tSource Directory: {source_directory}")
        print(f"\tBuild Directory: {build_directory}")
        print(f"\tBuild Type: {build_type.value}")
        print(f"\tCMake Toolchain: {toolchain_file}")
        print(f"\tChainload Toolchain: {chainload_toolchain_file}")
        # Start with the default arguments
        args: list[str | Path] = ["-S", source_directory,
                                  "-B", build_directory,
                                  f"-DCMAKE_BUILD_TYPE={build_type.value}"]
        # Append optional toolchain arguments
        if toolchain_file is not None:
            args.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}")
        if chainload_toolchain_file is not None:
            args.append(f"-DCHAOS_CHAINLOAD_TOOLCHAIN_FILE={chainload_toolchain_file}")
        # Append user-specified CMake cache variables
        if defines is not None:
            args.extend(CMake.format_defines(defines))
        # Append additional user-specified arguments
        if extra_args is not None:
            args.extend(extra_args)
        # Invoke `cmake` to generate files for the native build system
        self._run(args)

    def build(self, *,
              build_directory: Path,
              build_type: BuildType,
              parallel_level: int = None,
              clean_first: bool = True,
              extra_args: list[str] = None,
              native_args: list[str] = None) -> None:
        """
        Invoke `cmake` to build the project via the native build system
        :param build_directory: Path to the build directory in which files for the native build system are stored
        :param build_type: The build type (i.e., `Debug` or `Release`)
        :param parallel_level: The number of threads to build the project (Default: Unspecified, delegated to `cmake`)
        :param clean_first: Pass `True` to clean the build directory before building (Default: `True`)
        :param extra_args: Optional additional arguments passed to `cmake`
        :param native_args: Optional additional arguments passed to the native build system via `--`
        :raise `CalledProcessError` if `cmake` exits with a non-zero status code.
        """
        print(f"Building the project using CMake v{self.version}...")
        # Start with the default arguments
        args: list[str | Path] = ["--build", build_directory,
                                  "--config", build_type.value]
        # Append the clean-first argument if requested
        if clean_first:
            args.append("--clean-first")
        # Append the parallel level argument if specified
        if parallel_level is not None:
            args.extend(["--parallel", str(parallel_level)])
        # Append additional user-specified arguments
        if extra_args is not None:
            args.extend(extra_args)
        # Append native build system arguments
        if native_args is not None:
            args.append("--")
            args.extend(native_args)
        # Invoke `cmake` to build the project
        self._run(args)

    def install(self, *,
                build_directory: Path,
                prefix: Path = None,
                extra_args: list[str] = None) -> None:
        """
        Invoke `cmake` to install the project artifacts
        :param build_directory: Path to the build directory in which files for the native build system are stored
        :param prefix: Optional path to the directory under which to install the project artifacts
        :param extra_args: Optional additional arguments passed to `cmake`
        :raise `CalledProcessError` if `cmake` exits with a non-zero status code.
        """
        print(f"Installing project artifacts using CMake v{self.version}...")
        # Start with the default arguments
        args: list[str | Path] = ["--install", build_directory]
        # Append the prefix argument if specified
        if prefix is not None:
            args.extend(["--prefix", prefix])
        # Append additional user-specified arguments
        if extra_args is not None:
            args.extend(extra_args)
        # Invoke `cmake` to install the project artifacts
        self._run(args)
