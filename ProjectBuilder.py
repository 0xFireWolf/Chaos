#
# MARK: - Build, Test & Clean Projects
#

from .CompilerToolchainManager import *

kBuildFolder = "build"


# A project builder that builds, tests, and cleans the project
class ProjectBuilder:
    # Name of the executables that run all tests
    tests: list[str]

    def __init__(self, tests: list[str]):
        self.tests = tests

    def rebuild_project(self, btype: BuildType) -> None:
        """
        [Action] [Helper] Rebuild the project
        :param btype: The build type
        """
        self.clean_build_folder()
        os.mkdir(kBuildFolder)
        subprocess.run(["conan", "install", "..", "--build", "missing",
                        "--profile", "../" + kCurrentConanProfile], cwd=kBuildFolder)
        subprocess.run(["cmake", "-S", ".", "-B", kBuildFolder, "-DCMAKE_BUILD_TYPE={}".format(btype)])
        subprocess.run(["cmake", "--build", kBuildFolder, "--clean-first", "--parallel", str(os.cpu_count())])

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

    def run_all_tests(self) -> None:
        """
        [Action] Run all tests
        """
        for test in self.tests:
            subprocess.run([os.getcwd() + "/build/bin/" + test], cwd=kBuildFolder)

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
