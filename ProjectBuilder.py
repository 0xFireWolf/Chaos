#
# MARK: - Build, Test & Clean Projects
#
import glob
import platform
from typing import Any
from .CompilerToolchainManager import *

kBuildFolder = "build"


# A project builder that builds, tests, and cleans the project
class ProjectBuilder:
    def __init__(self, tests: list[str], source_folder: Path, exclude_patterns: list[str]):
        self.tests = tests
        # A path to the directory that contains all source files
        self.source_folder = source_folder
        # A regex pattern to exclude source files that are not of interest
        self.exclude_patterns = exclude_patterns

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

    #
    # MARK: - Code Coverage
    #

    def get_exclude_patterns_as_args(self, option: str) -> list[str]:
        """
        Convert the user-specified exclude patterns as arguments passed to the coverage analysis tool
        :param option: The command line tool option prepended to each exclude pattern
        :return: A list of command line arguments
        """
        args: list[str] = []
        if self.exclude_patterns is not None:
            for exclude_pattern in self.exclude_patterns:
                args.append(option)
                args.append(exclude_pattern)
        return args

    def get_cmake_variable_value(self, toolchain: Path, variable: str) -> str:
        """
        Get the value of a CMake variable defined in the given CMake Toolchain file
        :param toolchain: Path to a CMake Toolchain file
        :param variable: The name of a CMake variable
        :return: The value of the CMake variable on success.
        :raise: ValueError if the CMake variable of the given name does not exist.
        """
        with open(toolchain) as file:
            for line in file:
                result = re.search("set\\({}\\s*(.*?)\\s*\\)".format(variable), line)
                if result is not None:
                    return result.group(1)
            raise ValueError("Cannot find the path to the toolchain installation directory.")

    def get_gcov_path(self, toolchain: Path) -> Path:
        """
        Get the path to the `gcov` associated with the given CMake Toolchain file
        :param toolchain: Path to a CMake Toolchain file
        :return: The absolute path to `gcov`.
        """
        return Path(self.get_cmake_variable_value(toolchain, "GCOV")).resolve(strict=True)

    def get_llvm_profdata_path(self, toolchain: Path) -> Path:
        """
        Get the path to the `llvm-profdata` associated with the given CMake Toolchain file
        :param toolchain: Path to a CMake Toolchain file
        :return: The absolute path to `llvm-profdata`.
        """
        return Path(self.get_cmake_variable_value(toolchain, "LLVM_PROFDATA")).resolve(strict=True)

    def get_llvm_cov_path(self, toolchain: Path) -> Path:
        """
        Get the path to the `llvm-cov` associated with the given CMake Toolchain file
        :param toolchain: Path to a CMake Toolchain file
        :return: The absolute path to `llvm-cov`.
        """
        return Path(self.get_cmake_variable_value(toolchain, "LLVM_COV")).resolve(strict=True)

    def get_source_files_for_coverage(self) -> list[str]:
        """
        Get all source files to be considered when analyzing the code coverage
        :return: All the source files that will be analyzed for code coverage.
        """
        files = glob.glob(f"{str(self.source_folder.resolve())}/**/*.*pp", recursive=True)
        if self.exclude_patterns is not None:
            regex = re.compile("|".join([p.replace("*", ".*") for p in self.exclude_patterns]))
            return [file for file in files if not regex.search(file)]
        else:
            return files

    def get_cmake_generate_flags_for_coverage(self, compiler_flags: list[str]) -> list[str]:
        """
        Get the flags to be passed to CMake for generating files for the native build system
        :param compiler_flags: Special compiler flags needed to analyze the code coverage
        :return: A collection of additional CMake flags for build system generation.
        """
        flags = " ".join(compiler_flags)
        return [f"-DCMAKE_C_FLAGS='{flags}'", f"-DCMAKE_CXX_FLAGS='{flags}'"]

    def rebuild_and_run_all_tests_with_coverage_gcc(self) -> None:
        """
        Rebuild the project using GCC and run all tests to analyze code coverage using `Gcov`
        """
        gcov = self.get_gcov_path(kCurrentToolchainFile)
        working_directory = Path(os.getcwd()) / "build" / "bin"
        cmake_generate_flags = self.get_cmake_generate_flags_for_coverage(["-fprofile-arcs", "-ftest-coverage"])
        self.rebuild_project(BuildType.kDebug, cmake_generate_flags=cmake_generate_flags)
        self.run_all_tests()
        # Generate the code coverage report
        # https://stackoverflow.com/questions/55058715/how-to-get-correct-code-coverage-for-member-functions-in-header-files
        subprocess.run(["lcov", "--gcov-tool", gcov, "--capture", "--no-external",
                        "--directory", self.source_folder.resolve(),
                        "--directory", working_directory.parent / "CMakeFiles",
                        "--output-file", "Coverage.info"] + self.get_exclude_patterns_as_args("--exclude"),
                       cwd=working_directory).check_returncode()
        subprocess.run(["genhtml", "Coverage.info", "--output-directory", "CoverageReport"],
                       cwd=working_directory).check_returncode()

    def rebuild_and_run_all_tests_with_coverage_clang(self) -> None:
        """
        Rebuild the project using Clang and run all tests to analyze code coverage using `llvm-cov`
        """
        llvm_profdata = self.get_llvm_profdata_path(kCurrentToolchainFile)
        llvm_cov = self.get_llvm_cov_path(kCurrentToolchainFile)
        sources = self.get_source_files_for_coverage()
        working_directory = Path(os.getcwd()) / "build" / "bin"
        cmake_generate_flags = self.get_cmake_generate_flags_for_coverage(["-fprofile-instr-generate", "-fcoverage-mapping"])
        self.rebuild_project(BuildType.kDebug, cmake_generate_flags=cmake_generate_flags)
        print("Source files for coverage analysis:")
        for source in sources:
            print(f"- {source}")
        for test in self.tests:
            # Run the test and store the raw profile data to the given file
            self.run_test(test, env={"LLVM_PROFILE_FILE": f"{test}-%p.profraw"})
            # Merge all raw profile data into a single file
            subprocess.run([llvm_profdata, "merge", f"-output={test}.profdata"] +
                           glob.glob(str(working_directory / f"{test}-*.profraw")),
                           cwd=working_directory).check_returncode()
            # Generate the code coverage report as an HTML file
            with open(working_directory / f"{test}CoverageReport.html", "w") as fd:
                subprocess.run([llvm_cov, "show", test, f"-instr-profile={test}.profdata",
                                "-Xdemangler", "c++filt", "-Xdemangler", "-n",
                                "-show-branches=percent", "-use-color", "--format", "html"] + sources,
                               cwd=working_directory, stdout=fd).check_returncode()
            # Export the code coverage report as a LCOV file
            with open(working_directory / f"{test}CoverageReport.lcov", "w") as fd:
                subprocess.run([llvm_cov, "export", test, f"-instr-profile={test}.profdata",
                                "-Xdemangler", "c++filt", "-Xdemangler", "-n",
                                "-show-branch-summary", "-format=lcov"] + sources,
                               cwd=working_directory, stdout=fd).check_returncode()
            subprocess.run(["genhtml", f"{test}CoverageReport.lcov", "--output-directory", f"{test}CoverageReport"],
                           cwd=working_directory).check_returncode()

    def rebuild_and_run_all_tests_with_coverage_appleclang(self) -> None:
        raise NotImplementedError("Coverage with Apple Clang will be available soon.")

    def rebuild_and_run_all_tests_with_coverage_msvc(self) -> None:
        """
        Rebuild the project using GCC and run all tests to analyze code coverage using `OpenCppCoverage`
        """
        working_directory = Path(os.getcwd()) / "build" / "bin"
        self.rebuild_project(BuildType.kDebug)
        for test in self.tests:
            # https://github.com/OpenCppCoverage/OpenCppCoverage/wiki/FAQ#coverage-and-throw
            subprocess.run(["OpenCppCoverage", "--sources", self.source_folder,
                            "--excluded_line_regex", '\\s*\\}.*'] +
                           self.get_exclude_patterns_as_args("--excluded_sources") +
                           ["--", test],
                           cwd=working_directory).check_returncode()

    def rebuild_and_run_all_tests_with_coverage(self) -> None:
        """
        [Action] Rebuild the project and run all tests to analyze code coverage
        """
        # Guard: The source folder must not be none
        if self.source_folder is None:
            raise ValueError("The source folder must be specified to analyze the code coverage.")
        # Identify the compiler toolchain selected by the user
        compiler = Toolchain(Path(kCurrentToolchainFile).resolve().name).identifier.compiler.type
        if compiler == CompilerType.kGCC:
            self.rebuild_and_run_all_tests_with_coverage_gcc()
        elif compiler == CompilerType.kClang:
            self.rebuild_and_run_all_tests_with_coverage_clang()
        elif compiler == CompilerType.kAppleClang:
            self.rebuild_and_run_all_tests_with_coverage_appleclang()
        elif compiler == CompilerType.kMSVC:
            self.rebuild_and_run_all_tests_with_coverage_msvc()
        else:
            raise ValueError("Invalid compiler type reported by the current toolchain.")
