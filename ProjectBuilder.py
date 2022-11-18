#
# MARK: - Build, Test & Clean Projects
#
import glob
import platform
import subprocess
from typing import Any
from pathlib import Path
from .CompilerToolchainManager import *

kBuildFolder = "build"


# A project builder that builds, tests, and cleans the project
class ProjectBuilder:
    def __init__(self, tests: list[str]):
        self.tests = tests

    #
    # MARK: - Small Steps
    #

    def create_fresh_build_folder(self) -> None:
        """
        [Action] [Step] Create a fresh build folder
        """
        remove_folder_if_exists(kBuildFolder)
        os.mkdir(kBuildFolder)

    def conan_install(self, btype: BuildType, conan_flags: list[str] = None) -> None:
        """
        [Action] [Step] Install all required dependencies via Conan
        :param btype: The build type
        :param conan_flags: Additional flags passed to `conan`
        """
        profile = kCurrentConanProfileDebug if btype == BuildType.kDebug else kCurrentConanProfileRelease
        args: list[str] = ["conan", "install", ".", "-if", kBuildFolder, "--update", "--build", "missing", "--profile",
                           profile]
        if conan_flags is not None:
            args.extend(conan_flags)
        print("Installing all required packages via Conan...")
        print("Conan Args: \"{}\"".format(" ".join(args)))
        subprocess.run(args).check_returncode()

    def cmake_generate(self, btype: BuildType, cmake_flags: list[str] = None) -> None:
        """
        [Action] [Step] Use CMake to generate files for the native build system
        :param btype: The build type
        :param cmake_flags: Additional flags passed to `cmake`
        """
        args: list[str] = ["cmake", "-S", ".", "-B", kBuildFolder, "-DCMAKE_BUILD_TYPE={}".format(btype.value)]
        if cmake_flags is not None:
            args.extend(cmake_flags)
        print("Generating files for the native build system...")
        print("CMake Args: \"{}\"".format(" ".join(args)))
        subprocess.run(args).check_returncode()

    def cmake_build(self, btype: BuildType, parallel_level: int = os.cpu_count(), cmake_flags: list[str] = None,
                    build_flags: list[str] = None):
        """
        [Action] [Step] Use CMake to invoke the native build system to build the project
        :param btype: The build type
        :param parallel_level: The number of threads to build the project
        :param cmake_flags: Additional flags passed to `cmake`
        :param build_flags: Additional flags passed to the native build system
        """
        args: list[str] = ["cmake", "--build", kBuildFolder, "--config", btype.value, "--clean-first", "--parallel",
                           str(parallel_level)]
        if cmake_flags is not None:
            args.extend(cmake_flags)
        if build_flags is not None:
            args.append("--")
            args.extend(build_flags)
        print("Building the project...")
        print("CMake Args: \"{}\"".format(" ".join(args)))
        subprocess.run(args).check_returncode()

    #
    # MARK: - Rebuild Project
    #

    def rebuild_project(self, btype: BuildType, conan_flags: list[str] = None, cmake_generate_flags: list[str] = None,
                        cmake_build_flags: list[str] = None) -> None:
        """
        [Action] [Helper] Rebuild the project
        :param btype: The build type
        :param conan_flags: Additional flags passed to `conan`
        :param cmake_generate_flags: Additional flags passed to `cmake` before it generates files for the native build system
        :param cmake_build_flags: Additional flags passed to `cmake` before it builds the project using the native build system
        """
        self.create_fresh_build_folder()
        self.conan_install(btype, conan_flags)
        self.cmake_generate(btype, cmake_generate_flags)
        parallel_level = os.cpu_count()
        native_build_flags = None
        if platform.system() == "Windows":
            parallel_level = 1
            native_build_flags = ["/p:CL_MPCount={}".format(os.cpu_count())]
        self.cmake_build(btype, parallel_level, cmake_build_flags, native_build_flags)

    def rebuild_project_debug(self) -> None:
        """
        [Action] Rebuild the project in DEBUG mode
        """
        self.rebuild_project(BuildType.kDebug)

    def rebuild_project_release(self) -> None:
        """
        [Action] Rebuild the project in RELEASE mode
        """
        self.rebuild_project(BuildType.kRelease)

    #
    # MARK: - Clean Up
    #

    def clean_build_folder(self) -> None:
        """
        [Action] Clean and remove the build folder
        """
        remove_folder_if_exists(kBuildFolder)

    def clean_all(self) -> None:
        remove_folder_if_exists(kBuildFolder)
        remove_file_if_exist(kCurrentToolchainFile)
        remove_file_if_exist(kCurrentConanProfileDebug)
        remove_file_if_exist(kCurrentConanProfileRelease)
        remove_file_if_exist(kXcodeConfigFileDebug)
        remove_file_if_exist(kXcodeConfigFileRelease)

    #
    # MARK: - Run Tests
    #

    def run_test(self, name: str, cwd: str = None, env: dict[str, Any] = None) -> None:
        """
        [Action] Run a single test
        :param name: The name of the test
        :param cwd: The working directory under which to run the test
        :param env: The environment variables with which to run the test
        """
        directory = os.getcwd() + "/build/bin/"
        working_directory = directory if cwd is None else cwd
        environment = os.environ if env is None else os.environ.copy() | env
        print("========================================")
        print("Running test \"{}\"...".format(name))
        print(">> CWD = \"{}\"".format(working_directory))
        print(">> ENV = \"{}\"".format(env))
        print("========================================")
        subprocess.run([directory + name], cwd=working_directory, env=environment).check_returncode()

    def run_all_tests(self) -> None:
        """
        [Action] Run all tests
        """
        for test in self.tests:
            self.run_test(test)

    def rebuild_and_run_all_tests(self, btype: BuildType) -> None:
        """
        [Action] [Helper] Rebuild the project and run all tests
        :param btype: The build type
        """
        self.rebuild_project(btype)
        self.run_all_tests()

    def rebuild_and_run_all_tests_debug(self) -> None:
        """
        [Action] Run all tests in DEBUG mode
        """
        self.rebuild_and_run_all_tests(BuildType.kDebug)

    def rebuild_and_run_all_tests_release(self) -> None:
        """
        [Action] Run all tests in RELEASE mode
        """
        self.rebuild_and_run_all_tests(BuildType.kRelease)
