#
# MARK: - Build, Test & Clean Projects
#

from __future__ import annotations
from typing import Any
from pathlib import Path
import platform
import subprocess
import os
from .Project import Project
from .CMake import CMake
from .Conan import Conan
from .BuildSystemDescriptor import BuildType
from .Utilities import remove_folder_if_exists, remove_file_if_exists


# A project builder that builds, tests, and cleans the project
class ProjectBuilder:
    def __init__(self, project: Project, cmake: CMake, conan: Conan):
        """
        Initialize the project builder
        :param project: A C++ project to be built
        :param cmake: A handle to the `cmake` binary used to configure, build, and install the project
        :param conan: A handle to the `conan` binary used to install the project's dependencies
        """
        self.project = project
        self.cmake = cmake
        self.conan = conan

    #
    # MARK: - Choose Conan Profiles
    #

    def choose_conan_profiles(self, build_type: BuildType) -> tuple[Path, Path]:
        """
        Determine the pair of Conan profiles that will be used to install 3rd-party dependencies
        :param build_type: The build type
        :return: A pair of paths, in which the first path points to the current build profile to be used,
                 and the second path points to the current host profile to be used.
        """
        if build_type == BuildType.kDebug:
            return self.project.current_build_profile_debug_link_path, self.project.current_host_profile_debug_link_path
        else:
            return self.project.current_build_profile_release_link_path, self.project.current_host_profile_release_link_path

    #
    # MARK: - Construct Additional Conan Flags
    #

    def make_conan_flags(self, conan_flags: list[str] | None) -> list[str] | None:
        """
        Construct the final list of flags that will be passed to `conan install`
        :param conan_flags: A list of caller-provided flags
        :return: The merged list of project-level and caller-provided flags, or None if no flags are present.
        """
        flags = list[str]()
        if self.project.conan_flags is not None:
            flags.extend(self.project.conan_flags)
        if conan_flags is not None:
            flags.extend(conan_flags)
        return flags if len(flags) > 0 else None

    #
    # MARK: - Construct Additional CMake Flags
    #

    def make_cmake_generate_flags(self, cmake_generate_flags: list[str] | None) -> list[str] | None:
        """
        Construct the final list of flags to be passed to `cmake` during the generate step
        :param cmake_generate_flags: Additional flags provided by the caller.
        :return: The merged list of project-level and caller-provided flags, or None if no flags are present.
        """
        flags = list[str]()
        if self.project.cmake_generate_flags is not None:
            flags.extend(self.project.cmake_generate_flags)
        if cmake_generate_flags is not None:
            flags.extend(cmake_generate_flags)
        return flags if len(flags) > 0 else None

    def make_cmake_build_flags(self, cmake_build_flags: list[str] | None) -> list[str] | None:
        """
        Construct the final list of flags to be passed to `cmake` during the build step
        :param cmake_build_flags: Additional flags provided by the caller.
        :return: The merged list of project-level and caller-provided flags, or None if no flags are present.
        """
        flags = list[str]()
        if self.project.cmake_build_flags is not None:
            flags.extend(self.project.cmake_build_flags)
        if cmake_build_flags is not None:
            flags.extend(cmake_build_flags)
        return flags if len(flags) > 0 else None

    #
    # MARK: - Rebuild Project
    #

    def create_fresh_build_folder(self) -> None:
        """
        Create a fresh build folder
        """
        remove_folder_if_exists(self.project.build_directory)
        os.mkdir(self.project.build_directory)

    def configure(self,
                  build_type: BuildType,
                  conan_flags: list[str] | None = None,
                  cmake_generate_flags: list[str] | None = None) -> None:
        """
        Configure the project
        :param build_type: The build type
        :param conan_flags: Optional additional arguments passed to `conan install`
        :param cmake_generate_flags: Optional additional arguments passed to `cmake` during the generate step
        """
        # Determine which pair of Conan profiles will be used to install 3rd-party dependencies
        build_profile, host_profile = self.choose_conan_profiles(build_type)

        # Retrieve the CMake toolchain file that will be used to configure the project
        toolchain_file = self.project.current_toolchain_link_path
        chainload_toolchain_file = self.project.build_directory / self.conan.integration_file_name

        # Check whether the bundled libc++ library should be used on macOS
        # TODO: The env var has been renamed to CHAOS_XXXX
        if int(os.getenv("CHAOS_USE_BUNDLED_LIBCPP", 0)) == 1:
            defines = {"CHAOS_USE_BUNDLED_LIBCPP": "ON"}
        else:
            defines = None

        # Create a fresh build folder
        self.create_fresh_build_folder()

        # Install all 3rd-party dependencies via Conan
        self.conan.install(source_directory=self.project.source_directory,
                           output_directory=self.project.build_directory,
                           build_profile=build_profile,
                           host_profile=host_profile,
                           extra_args=self.make_conan_flags(conan_flags))

        # Generate files for the native build system using CMake
        self.cmake.generate(source_directory=self.project.source_directory,
                            build_directory=self.project.build_directory,
                            build_type=build_type,
                            toolchain_file=toolchain_file,
                            chainload_toolchain_file=chainload_toolchain_file,
                            defines=defines,
                            extra_args=self.make_cmake_generate_flags(cmake_generate_flags))

    def rebuild_project(self,
                        build_type: BuildType,
                        conan_flags: list[str] | None = None,
                        cmake_generate_flags: list[str] | None = None,
                        cmake_build_flags: list[str] | None = None) -> None:
        """
        Rebuild the project
        :param build_type: The build type
        :param conan_flags: Optional additional arguments passed to `conan install`
        :param cmake_generate_flags: Optional additional arguments passed to `cmake` during the generate step
        :param cmake_build_flags: Optional additional arguments passed to `cmake` during the build step
        """
        # Configure the project
        self.configure(build_type, conan_flags, cmake_generate_flags)

        # Determine the flags passed to the native build system
        if platform.system() == "Windows":
            native_build_flags = [f"/p:CL_MPCount={os.cpu_count()}"]
            parallel_level = 1
        else:
            native_build_flags = None
            parallel_level = os.cpu_count()

        # Build the project
        self.cmake.build(build_directory=self.project.build_directory,
                         build_type=build_type,
                         parallel_level=parallel_level,
                         clean_first=True,
                         extra_args=self.make_cmake_build_flags(cmake_build_flags),
                         native_args=native_build_flags)

    # Action
    def rebuild_project_debug(self) -> None:
        """
        [Action] Rebuild the project in DEBUG mode
        """
        self.rebuild_project(BuildType.kDebug)

    # Action
    def rebuild_project_release(self) -> None:
        """
        [Action] Rebuild the project in RELEASE mode
        """
        self.rebuild_project(BuildType.kRelease)

    # Action
    def install_project(self, prefix: Path | None = None) -> None:
        """
        [Action] Install all project artifacts
        """
        self.cmake.install(build_directory=self.project.build_directory, prefix=prefix)

    #
    # MARK: - Clean Up
    #

    # Action
    def clean_build_folder(self) -> None:
        """
        [Action] Clean and remove the build folder
        """
        remove_folder_if_exists(self.project.build_directory)

    # Action
    def clean_all(self) -> None:
        """
        [Action] Remove the build folder and the links to the selected compiler toolchain files
        """
        remove_folder_if_exists(self.project.build_directory)
        remove_file_if_exists(self.project.current_toolchain_link_path)
        remove_file_if_exists(self.project.current_build_profile_debug_link_path)
        remove_file_if_exists(self.project.current_build_profile_release_link_path)
        remove_file_if_exists(self.project.current_host_profile_debug_link_path)
        remove_file_if_exists(self.project.current_host_profile_release_link_path)

    # Action
    def remove_all_packages(self) -> None:
        """
        [Action] Remove all conan packages
        """
        self.conan.remove_all()

    #
    # MARK: - Run Tests
    #

    # Action
    def run_test(self,
                 name: str,
                 build_type: BuildType,
                 cwd: Path | None = None,
                 env: dict[str, Any] | None = None) -> None:
        """
        [Action] Run a single test
        :param name: The name of the test
        :param build_type: The build type
        :param cwd: The working directory under which to run the test
        :param env: The environment variables with which to run the test
        """
        directory = self.project.build_directory
        # Win32 Builds: "CMAKE_BINARY_DIR / <CONFIG>"
        if platform.system() == "Windows":
            directory /= build_type.value
        working_directory = directory if cwd is None else cwd
        environment = os.environ if env is None else os.environ.copy() | env
        print("========================================")
        print(f"Running test '{name}'...")
        print("========================================")
        subprocess.run([directory / name], cwd=working_directory, env=environment).check_returncode()

    # Action
    def run_all_tests(self, build_type: BuildType) -> None:
        """
        [Action] Run all tests
        :param build_type: The build type
        """
        for test in self.project.test_executables:
            self.run_test(test, build_type)

    def rebuild_and_run_all_tests(self, build_type: BuildType) -> None:
        """
        [Action] [Helper] Rebuild the project and run all tests
        :param build_type: The build type
        """
        self.rebuild_project(build_type)
        self.run_all_tests(build_type)

    # Action
    def rebuild_and_run_all_tests_debug(self) -> None:
        """
        [Action] Run all tests in DEBUG mode
        """
        self.rebuild_and_run_all_tests(BuildType.kDebug)

    # Action
    def rebuild_and_run_all_tests_release(self) -> None:
        """
        [Action] Run all tests in RELEASE mode
        """
        self.rebuild_and_run_all_tests(BuildType.kRelease)

    def rebuild_and_run_all_tests_with_coverage(self) -> None:
        """
        [Action] Run all tests with code coverage
        """
        print("Running tests with code coverage is not supported by Chaos v2 at the moment.")
