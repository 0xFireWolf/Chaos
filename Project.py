#
# MARK: - Describe a Project
#
from __future__ import annotations
from pathlib import Path
from .AdditionalToolsInstaller import AdditionalToolsInstaller


class Project:
    def __init__(self,
                 name: str,
                 build_directory_name: str = "build",
                 cmake_toolchains_directory_name: str = "Toolchains",
                 conan_profiles_directory_name: str = "Profiles",
                 conan_flags: list[str] | None = None,
                 cmake_generate_flags: list[str] | None = None,
                 cmake_build_flags: list[str] | None = None,
                 test_executables: list[str] | None = None,
                 coverage_source_directory_name: str = "Sources",
                 coverage_exclude_patterns: list[str] | None = None,
                 additional_tools_installer: AdditionalToolsInstaller | None = None):
        # The project name
        self.name = name

        # A path to the source directory in which `CMakeLists.txt` and `conanfile.txt/py` can be found
        self.source_directory: Path = Path.cwd()

        # A path to the build directory in which Conan toolchains and project binaries will be stored
        self.build_directory: Path = self.source_directory / build_directory_name

        # A path to the directory in which all CMake toolchain files can be found
        self.cmake_toolchains_directory: Path = self.source_directory / cmake_toolchains_directory_name

        # A path to the directory in which all Conan profiles can be found
        self.conan_profiles_directory: Path = self.source_directory / conan_profiles_directory_name

        # A list of additional flags passed to Conan when installing 3rd-party libraries
        self.conan_flags: list[str] | None = conan_flags

        # A list of additional flags passed to CMake when generating files for the native build system
        self.cmake_generate_flags: list[str] | None = cmake_generate_flags

        # A list of additional flags passed to CMake when building the project
        self.cmake_build_flags: list[str] | None = cmake_build_flags

        # Name of each executable that contains unit tests
        self.test_executables: list[str] = [f"{name}Tests"] if test_executables is None else test_executables

        # A path to the source directory in which all C/C++ files for coverage analysis can be found
        self.coverage_source_directory: Path = self.source_directory / coverage_source_directory_name

        # A list of regex patterns that can be used to exclude source files from coverage analysis
        self.coverage_exclude_patterns: list[str] = [] if coverage_exclude_patterns is None else coverage_exclude_patterns

        # An installer that can be used to install additional development tools needed to build this project
        self.additional_tools_installer: AdditionalToolsInstaller = additional_tools_installer or AdditionalToolsInstaller()

    @property
    def current_toolchain_link_path(self) -> Path:
        return self.source_directory / "CurrentToolchain.cmake"

    @property
    def current_build_profile_debug_link_path(self) -> Path:
        return self.source_directory / "CurrentBuildProfileDebug.conanprofile"

    @property
    def current_build_profile_release_link_path(self) -> Path:
        return self.source_directory / "CurrentBuildProfileRelease.conanprofile"

    @property
    def current_host_profile_debug_link_path(self) -> Path:
        return self.source_directory / "CurrentHostProfileDebug.conanprofile"

    @property
    def current_host_profile_release_link_path(self) -> Path:
        return self.source_directory / "CurrentHostProfileRelease.conanprofile"
