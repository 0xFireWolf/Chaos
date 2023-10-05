#
# MARK: - Build, Test & Clean Projects
#
from __future__ import annotations
from typing import Any
from .CompilerToolchainManager import *
from .CMakeManager import CMakeManager, CMake
from .Project import Project
import glob
import platform

kConanCMakeIntegrationFileV1 = "conan_paths.cmake"
kConanCMakeIntegrationFileV2 = "conan_toolchain.cmake"


# A project builder that builds, tests, and cleans the project
class ProjectBuilder:
    def __init__(self, project: Project, cmake_manager: CMakeManager):
        """
        Initialize the project builder
        :param project: A C++ project to be built
        :param cmake_manager: A CMake manager for the current system
        """
        self.project = project
        self.cmake_manager = cmake_manager

    #
    # MARK: - Small Steps
    #

    def create_fresh_build_folder(self) -> None:
        """
        [Action] [Step] Create a fresh build folder
        """
        remove_folder_if_exists(self.project.build_directory)
        os.mkdir(self.project.build_directory)

    def conan_install(self,
                      build_profile: Path,
                      host_profile: Path,
                      conan_flags: list[str] = None) -> None:
        """
        [Action] [Step] Install all required dependencies via Conan 1.x or 2.x
        :param build_profile: Path to a Conan profile that is used to build all dependencies on the host machine
        :param host_profile: Path to a Conan profile that is used to host all dependencies on the target machine
        :param conan_flags: Additional flags passed to `conan`
        """
        args = []
        if is_conan_v2_installed():
            args.extend(["conan", "install", self.project.source_directory,
                         "--output-folder", self.project.build_directory,
                         "--update", "--build", "missing",
                         "--profile:build", build_profile, "--profile:host", host_profile])
        else:
            if build_profile != host_profile:
                raise ValueError("Cross compiling with two separated profiles is not supported by Conan 1.x.")
            args.extend(["conan", "install", self.project.source_directory,
                         "--install-folder", self.project.build_directory,
                         "--update", "--build", "missing",
                         "--profile", build_profile])
        # Append Conan flags specified by the project
        if self.project.conan_flags is not None:
            args.extend(self.project.conan_flags)
        # Append Conan flags specified by the caller
        if conan_flags is not None:
            args.extend(conan_flags)
        print("Installing all required packages via Conan...", flush=True)
        print(f"Conan Args: {' '.join([str(arg) for arg in args])}", flush=True)
        subprocess.run(args).check_returncode()

    def cmake_generate(self,
                       cmake: CMake,
                       build_type: BuildType,
                       toolchain_file: Path,
                       chainload_toolchain_file: Path,
                       cmake_flags: list[str] = None) -> None:
        """
        [Action] [Step] Use CMake to generate files for the native build system
        :param cmake: The CMake binary that will be used to generate files for the native build system
        :param build_type: The build type
        :param toolchain_file: Path to the primary CMake toolchain file
        :param chainload_toolchain_file: Path to the secondary CMake toolchain file
        :param cmake_flags: Additional flags passed to `cmake`
        """
        print(f"Generating files for the native build system using CMake v{cmake.major}.{cmake.minor}.{cmake.patch}...")
        print(f"\tSource Directory: {self.project.source_directory}")
        print(f"\tBuild Directory: {self.project.build_directory}")
        print(f"\tBuild Type: {build_type.value}")
        print(f"\tCMake Toolchain: {toolchain_file}")
        print(f"\tChainload Toolchain: {chainload_toolchain_file}")
        args = ["-S", self.project.source_directory,
                "-B", self.project.build_directory,
                f"-DCMAKE_BUILD_TYPE={build_type.value}",
                f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
                f"-DCHAOS_CHAINLOAD_TOOLCHAIN_FILE={chainload_toolchain_file}"]
        if cmake_flags is not None:
            args.extend(cmake_flags)
        cmake.call(args)

    def cmake_build(self,
                    cmake: CMake,
                    build_type: BuildType,
                    parallel_level: int = os.cpu_count(),
                    cmake_flags: list[str] = None,
                    build_flags: list[str] = None) -> None:
        """
        [Action] [Step] Use CMake to invoke the native build system to build the project
        :param cmake: The CMake binary that will be used to invoke the native build system to build the project
        :param build_type: The build type
        :param parallel_level: The number of threads to build the project
        :param cmake_flags: Additional flags passed to `cmake`
        :param build_flags: Additional flags passed to the native build system
        """
        print(f"Building the project using CMake v{cmake.major}.{cmake.minor}.{cmake.patch}...")
        args = ["--build", self.project.build_directory,
                "--config", build_type.value,
                "--clean-first",
                "--parallel", str(parallel_level)]
        if cmake_flags is not None:
            args.extend(cmake_flags)
        if build_flags is not None:
            args.append("--")
            args.extend(build_flags)
        cmake.call(args)

    def cmake_install(self, cmake: CMake, prefix: Path = None) -> None:
        """
        [Action] [Step] Use CMake to install the project artifacts
        :param cmake: The CMake binary that will be used to install all artifacts
        :param prefix: The installation prefix
        """
        print(f"Installing project artifacts using CMake v{cmake.major}.{cmake.minor}.{cmake.patch}...")
        args = ["--install", self.project.build_directory]
        if prefix is not None:
            args.extend(["--prefix", prefix])
        cmake.call(args)

    #
    # MARK: - Rebuild Project
    #

    def configure(self,
                  cmake: CMake,
                  build_type: BuildType,
                  conan_flags: list[str] = None,
                  cmake_generate_flags: list[str] = None) -> None:
        """
        [Action] [Helper] Configure the project
        :param cmake: The CMake binary that will be used to invoke the native build system to build the project
        :param build_type: The build type
        :param conan_flags: Additional flags passed to `conan`
        :param cmake_generate_flags: Additional flags passed to `cmake` when generates files for the native build system
        """
        # Compute required properties for Conan
        if build_type == BuildType.kDebug:
            build_profile = kCurrentConanBuildProfileDebug
            host_profile = kCurrentConanHostProfileDebug
        else:
            build_profile = kCurrentConanBuildProfileRelease
            host_profile = kCurrentConanHostProfileRelease

        # Compute required properties for CMake
        toolchain_file = self.project.source_directory / kCurrentToolchainFile
        chainload_file = self.project.build_directory / (kConanCMakeIntegrationFileV2
                                                         if is_conan_v2_installed()
                                                         else kConanCMakeIntegrationFileV1)

        # Configure the project
        self.create_fresh_build_folder()
        self.conan_install(build_profile, host_profile, conan_flags)
        self.cmake_generate(cmake, build_type, toolchain_file, chainload_file, cmake_generate_flags)

    def rebuild_project(self,
                        build_type: BuildType,
                        conan_flags: list[str] = None,
                        cmake_generate_flags: list[str] = None,
                        cmake_build_flags: list[str] = None) -> None:
        """
        [Action] [Helper] Rebuild the project
        :param build_type: The build type
        :param conan_flags: Additional flags passed to `conan`
        :param cmake_generate_flags: Additional flags passed to `cmake` when generates files for the native build system
        :param cmake_build_flags: Additional flags passed to `cmake` when building the project
        """
        # Get the default CMake
        cmake = CMake.default()

        # Calculate required properties for the native build system
        native_build_flags = None
        parallel_level = os.cpu_count()
        if platform.system() == "Windows":
            native_build_flags = [f"/p:CL_MPCount={parallel_level}"]
            parallel_level = 1

        # Rebuild the project
        self.configure(cmake, build_type, conan_flags, cmake_generate_flags)
        self.cmake_build(cmake, build_type, parallel_level, cmake_build_flags, native_build_flags)

    # Action
    def rebuild_project_debug(self,
                              conan_flags: list[str] = None,
                              cmake_generate_flags: list[str] = None,
                              cmake_build_flags: list[str] = None) -> None:
        """
        [Action] Rebuild the project in DEBUG mode
        :param conan_flags: Additional flags passed to `conan`
        :param cmake_generate_flags: Additional flags passed to `cmake` when generates files for the native build system
        :param cmake_build_flags: Additional flags passed to `cmake` when building the project
        """
        self.rebuild_project(BuildType.kDebug, conan_flags, cmake_generate_flags, cmake_build_flags)

    # Action
    def rebuild_project_release(self,
                                conan_flags: list[str] = None,
                                cmake_generate_flags: list[str] = None,
                                cmake_build_flags: list[str] = None) -> None:
        """
        [Action] Rebuild the project in RELEASE mode
        :param conan_flags: Additional flags passed to `conan`
        :param cmake_generate_flags: Additional flags passed to `cmake` when generates files for the native build system
        :param cmake_build_flags: Additional flags passed to `cmake` when building the project
        """
        self.rebuild_project(BuildType.kRelease, conan_flags, cmake_generate_flags, cmake_build_flags)

    # Action
    def install_project(self, prefix: Path = None) -> None:
        """
        [Action] Install all project artifacts
        """
        self.cmake_install(CMake.default(), prefix)

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
        remove_folder_if_exists(self.project.build_directory)
        remove_file_if_exist(kCurrentToolchainFile)
        remove_file_if_exist(kCurrentConanBuildProfileDebug)
        remove_file_if_exist(kCurrentConanBuildProfileRelease)
        remove_file_if_exist(kCurrentConanHostProfileDebug)
        remove_file_if_exist(kCurrentConanHostProfileRelease)
        remove_file_if_exist(kXcodeConfigFileDebug)
        remove_file_if_exist(kXcodeConfigFileRelease)

    #
    # MARK: - Run Tests
    #

    # Action
    def run_test(self, name: str, build_type: BuildType, cwd: Path = None, env: dict[str, Any] = None) -> None:
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

    #
    # MARK: - Determine Minimum CMake Version
    #

    def determine_minimum_cmake_version(self, min_major: int, min_minor: int, to_directory: Path) -> None:
        """
        [Helper] Determine the minimum version of CMake needed to configure the project
        :param min_major: The minimum major version of CMake from which to start the search
        :param min_minor: The minimum minor version of CMake from which to start the search
        :param to_directory: Path to the directory to store the extracted CMake binary
        """
        results = dict[CMake, bool]()
        for cmake in self.cmake_manager.get_cmake_binaries(min_major, min_minor, to_directory, True):
            try:
                self.configure(cmake, BuildType.kRelease)
                results[cmake] = True
            except subprocess.CalledProcessError:
                results[cmake] = False
        print("\n\n")
        print("=====================")
        print("Summary of Execution:")
        print("=====================")
        for cmake, outcome in results.items():
            print(f"[{'SUCCESS' if outcome else 'FAILURE'}] CMake v{cmake.major}.{cmake.minor}.{cmake.patch}")

    def determine_minimum_cmake_version_interactive(self) -> None:
        """
        [Action] Determine the minimum version of CMake needed to configure the project
        """
        try:
            min_major = int(input("Enter the minimum major version of CMake to start the search: "))
            min_minor = int(input("Enter the minimum minor version of CMake to start the search: "))
            directory = input("Enter the path to directory to store CMake binaries. "
                              "(Default: A Temporary Folder): ").strip()
            if not directory:
                with tempfile.TemporaryDirectory() as temp_directory:
                    self.determine_minimum_cmake_version(min_major, min_minor, Path(temp_directory))
            else:
                self.determine_minimum_cmake_version(min_major, min_minor, Path(directory))
        except ValueError:
            print("Invalid input. Please try again.")

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
        if self.project.coverage_exclude_patterns is not None:
            for exclude_pattern in self.project.coverage_exclude_patterns:
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
        files = glob.glob(f"{str(self.project.coverage_source_directory.resolve())}/**/*.*pp", recursive=True)
        if self.project.coverage_exclude_patterns is not None:
            regex = re.compile("|".join([p.replace("*", ".*") for p in self.project.coverage_exclude_patterns]))
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
        working_directory = self.project.build_directory
        cmake_generate_flags = self.get_cmake_generate_flags_for_coverage(["-fprofile-arcs", "-ftest-coverage"])
        self.rebuild_project(BuildType.kDebug, cmake_generate_flags=cmake_generate_flags)
        self.run_all_tests(BuildType.kDebug)
        # Generate the code coverage report
        # https://stackoverflow.com/questions/55058715/how-to-get-correct-code-coverage-for-member-functions-in-header-files
        subprocess.run(["lcov", "--gcov-tool", gcov, "--capture", "--no-external",
                        "--directory", self.project.coverage_source_directory.resolve(),
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
        working_directory = self.project.build_directory
        cmake_generate_flags = self.get_cmake_generate_flags_for_coverage(["-fprofile-instr-generate",
                                                                           "-fcoverage-mapping"])
        self.rebuild_project(BuildType.kDebug, cmake_generate_flags=cmake_generate_flags)
        print("Source files for coverage analysis:")
        for source in sources:
            print(f"- {source}")
        for test in self.project.test_executables:
            # Run the test and store the raw profile data to the given file
            self.run_test(test, BuildType.kDebug, env={"LLVM_PROFILE_FILE": f"{test}-%p.profraw"})
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
        # TODO: Need to specify the path to the debug build
        working_directory = self.project.build_directory / BuildType.kDebug.value
        self.rebuild_project(BuildType.kDebug)
        for test in self.project.test_executables:
            # https://github.com/OpenCppCoverage/OpenCppCoverage/wiki/FAQ#coverage-and-throw
            subprocess.run(["OpenCppCoverage", "--sources", self.project.coverage_source_directory,
                            "--excluded_line_regex", '\\s*\\}.*'] +
                           self.get_exclude_patterns_as_args("--excluded_sources") +
                           ["--", test],
                           cwd=working_directory).check_returncode()

    def rebuild_and_run_all_tests_with_coverage(self) -> None:
        """
        [Action] Rebuild the project and run all tests to analyze code coverage
        """
        # Guard: The source folder must not be none
        if self.project.coverage_source_directory is None:
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
