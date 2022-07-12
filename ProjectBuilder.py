#
# MARK: - Build, Test & Clean Projects
#
import os
import pathlib

from .CompilerToolchainManager import *

kBuildFolder = "build"


# A project builder that builds, tests, and cleans the project
class ProjectBuilder:
    def __init__(self, tests: list[str]):
        self.tests = tests

    def rebuild_project(self, btype: BuildType) -> None:
        """
        [Action] [Helper] Rebuild the project
        :param btype: The build type
        """
        self.clean_build_folder()
        os.mkdir(kBuildFolder)
        profile = kCurrentConanProfileDebug if btype == BuildType.kDebug else kCurrentConanProfileRelease
        subprocess.run(["conan", "install", "..", "--build", "missing", "--profile", "../" + profile], cwd=kBuildFolder).check_returncode()
        subprocess.run(["cmake", "-S", ".", "-B", kBuildFolder, "-DCMAKE_BUILD_TYPE={}".format(btype)]).check_returncode()
        subprocess.run(["cmake", "--build", kBuildFolder, "--config", btype.value, "--clean-first", "--parallel", str(os.cpu_count())]).check_returncode()

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
        if os.path.exists(kBuildFolder):
            shutil.rmtree(kBuildFolder)

    def clean_all(self) -> None:
        self.clean_build_folder()
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
