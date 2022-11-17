#
# MARK: - Build, Test & Clean Projects
#

import platform

from .CompilerToolchainManager import *

kBuildFolder = "build"


# A project builder that builds, tests, and cleans the project
class ProjectBuilder:
    def __init__(self, tests: list[str]):
        self.tests = tests

    def create_fresh_build_folder(self) -> None:
        """
        [Action] [Step] Create a fresh build folder
        """
        remove_folder_if_exists(kBuildFolder)
        os.mkdir(kBuildFolder)

    def conan_install(self, btype: BuildType) -> None:
        """
        [Action] [Step] Install all required dependencies via Conan
        :param btype: The build type
        """
        profile = kCurrentConanProfileDebug if btype == BuildType.kDebug else kCurrentConanProfileRelease
        subprocess.run(["conan", "install", ".", "-if", kBuildFolder, "--update", "--build", "missing", "--profile", profile]).check_returncode()

    def cmake_generate(self, btype: BuildType, cmake_flags: list[str] = None) -> None:
        """
        [Action] [Step] Use CMake to generate files for the native build system
        :param btype: The build type
        :param cmake_flags: Additional flags passed to `cmake`
        """
        args = ["cmake", "-S", ".", "-B", kBuildFolder, "-DCMAKE_BUILD_TYPE={}".format(btype)]
        if cmake_flags is not None:
            args.append(cmake_flags)
        print("[G] CMake Args: \"{}\"", " ".join(args))
        subprocess.run(args).check_returncode()

    def cmake_build(self, btype: BuildType, parallel_level: int = os.cpu_count(), cmake_flags: list[str] = None, build_flags: list[str] = None):
        """
        [Action] [Step] Use CMake to invoke the native build system to build the project
        :param btype: The build type
        :param parallel_level: The number of threads to build the project
        :param cmake_flags: Additional flags passed to `cmake`
        :param build_flags: Additional flags passed to the native build system
        """
        args = ["cmake", "--build", kBuildFolder, "--config", btype.value, "--clean-first", "--parallel", str(parallel_level)]
        if cmake_flags is not None:
            args.append(cmake_flags)
        if build_flags is not None:
            args.append(["--"])
            args.append(build_flags)
        print("[B] CMake Args: \"{}\"", " ".join(args))
        subprocess.run(args).check_returncode()

    def rebuild_project(self, btype: BuildType) -> None:
        """
        [Action] [Helper] Rebuild the project
        :param btype: The build type
        """
        self.create_fresh_build_folder()
        self.conan_install(btype)
        self.cmake_generate(btype)
        if platform.system() == "Windows":
            self.cmake_build(btype, 1, None, ["/p:CL_MPCount={}".format(os.cpu_count())])
        else:
            self.cmake_build(btype)

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

    def run_all_tests(self) -> None:
        """
        [Action] Run all tests
        """
        directory = os.getcwd() + "/build/bin/"
        for test in self.tests:
            print("========================================")
            print("Running test \"{}\"...".format(test))
            print("========================================")
            subprocess.run([directory + test], cwd=directory).check_returncode()

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
