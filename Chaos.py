#
# MARK: - Chaos Control Center
#
from __future__ import annotations
import argparse
import distro
import traceback
from subprocess import CalledProcessError
from typing import Type
from .EnvironmentConfigurator import *
from .ProjectBuilder import *
from .CMakeManager import CMakeManagerMacOS, CMakeManagerLinux, CMakeManagerWindows
from .Menu import Menu


class Chaos:
    def __init__(self, project: Project):
        """
        Initialize the Chaos Control Center for the given project
        :param project: A project whose chaos to be controlled
        """
        system = platform.system()
        machine = platform.machine()
        if system == "Darwin":
            architecture = Architecture.kx86_64 if machine == "x86_64" else Architecture.kARM64
            self.configurator = EnvironmentConfiguratorMacOS(project.additional_tools_installer.macos)
            self.toolchain_manager = CompilerToolchainManagerMacOS(architecture)
            self.project_builder = ProjectBuilder(project, CMakeManagerMacOS())
            self.clear_console = lambda: os.system("clear")
        elif system == "Linux":
            distribution = distro.id()
            version = distro.version()
            if distribution == "ubuntu":
                self.configurator = EnvironmentConfiguratorUbuntu(project.additional_tools_installer.ubuntu)
                if version == "20.04":
                    self.toolchain_manager = CompilerToolchainManagerUbuntu2004(Architecture.kx86_64)
                elif version == "22.04":
                    self.toolchain_manager = CompilerToolchainManagerUbuntu2204(Architecture.kx86_64)
                elif version == "24.04":
                    self.toolchain_manager = CompilerToolchainManagerUbuntu2404(Architecture.kx86_64)
                else:
                    print(f"Ubuntu {version} is not tested.")
                    raise EnvironmentError
                self.project_builder = ProjectBuilder(project, CMakeManagerLinux())
                self.clear_console = lambda: os.system("clear")
            else:
                print(f"{distro.name(True)} is not supported.")
                raise EnvironmentError
        elif system == "Windows":
            self.configurator = EnvironmentConfiguratorWindows(project.additional_tools_installer.windows)
            self.toolchain_manager = CompilerToolchainManagerWindows(Architecture.kx86_64)
            self.project_builder = ProjectBuilder(project, CMakeManagerWindows())
            self.clear_console = lambda: os.system("cls")
        elif system == "FreeBSD":
            self.configurator = EnvironmentConfiguratorFreeBSD(project.additional_tools_installer.freebsd)
            self.toolchain_manager = CompilerToolchainManagerFreeBSD(Architecture.kx86_64)
            self.project_builder = ProjectBuilder(project, CMakeManager())  # CMakeManager does not support FreeBSD
            self.clear_console = lambda: os.system("clear")
        else:
            print(f"{system} is not supported.")
            raise EnvironmentError

    #
    # MARK: Chaos Running in Chaos Mode
    #

    def ci_install_tools(self) -> None:
        """
        [CI] Install all required development tools
        """
        self.configurator.install_all()

    def ci_install_toolchain(self, name: str) -> None:
        """
        [CI] Install the toolchain that has the given name
        :param name: The toolchain name
        :raise `KeyError` if the given name is invalid;
               `CalledProcessError` if failed to install the toolchain.
        """
        match name:
            case "gcc-10": return self.toolchain_manager.install_gcc_10()
            case "gcc-11": return self.toolchain_manager.install_gcc_11()
            case "gcc-12": return self.toolchain_manager.install_gcc_12()
            case "gcc-13": return self.toolchain_manager.install_gcc_13()
            case "gcc-14": return self.toolchain_manager.install_gcc_14()
            case "gcc-15": return self.toolchain_manager.install_gcc_15()
            case "clang-13": return self.toolchain_manager.install_clang_13()
            case "clang-14": return self.toolchain_manager.install_clang_14()
            case "clang-15": return self.toolchain_manager.install_clang_15()
            case "clang-16": return self.toolchain_manager.install_clang_16()
            case "clang-17": return self.toolchain_manager.install_clang_17()
            case "clang-18": return self.toolchain_manager.install_clang_18()
            case "clang-19": return self.toolchain_manager.install_clang_19()
            case "clang-20": return self.toolchain_manager.install_clang_20()
            case "apple-clang-13": return self.toolchain_manager.install_apple_clang_13()
            case "apple-clang-14": return self.toolchain_manager.install_apple_clang_14()
            case "apple-clang-15": return self.toolchain_manager.install_apple_clang_15()
            case "apple-clang-16": return self.toolchain_manager.install_apple_clang_16()
            case "apple-clang-17": return self.toolchain_manager.install_apple_clang_17()
            case _: raise KeyError(f"{name} is not a valid compiler toolchain.")

    def ci_select_toolchain(self, build_name: str, host_name: str = None) -> None:
        """
        [CI] Select the toolchain that has the given name
        :param build_name: The name of the toolchain that specifies the build environment
        :param host_name: The name of the toolchain that specifies the host environment
        :raise `ValueError` if the given toolchain name is invalid;
               `CalledProcessError` if failed to select the toolchain.
        """
        cmake_toolchain = Toolchain(build_name + ".cmake")
        build_profile_dbg = ConanProfile(build_name + "_Debug.conanprofile")
        build_profile_rel = ConanProfile(build_name + "_Release.conanprofile")
        host_profile_dbg = None if host_name is None else ConanProfile(host_name + "_Debug.conanprofile")
        host_profile_rel = None if host_name is None else ConanProfile(host_name + "_Release.conanprofile")
        self.toolchain_manager.apply_compiler_toolchain(cmake_toolchain,
                                                        build_profile_dbg,
                                                        build_profile_rel,
                                                        host_profile_dbg,
                                                        host_profile_rel)

    def ci_build_all(self, build_type: str, cmake_generate_flags: list[str] = None) -> None:
        """
        [CI] Build all targets
        :param build_type: The raw build type
        :param cmake_generate_flags: Additional flags passed to `cmake` when generates files for the native build system
        :raise `ValueError` if the given build type is invalid;
               `CalledProcessError` if failed to build one of the targets.
        """
        self.project_builder.rebuild_project(BuildType(build_type), cmake_generate_flags=cmake_generate_flags)

    def ci_run_tests(self, build_type: str) -> None:
        """
        [CI] Run all tests
        :param build_type: The raw build type
        :raise `ValueError` if the given build type is invalid;
               `CalledProcessError` if one of the tests has failed.
        """
        self.project_builder.run_all_tests(BuildType(build_type))

    def ci_run_tests_with_coverage(self) -> None:
        """
        [CI] Run all tests and analyze code coverage
        :raise `CalledProcessError` if one of the tests has failed.
        """
        self.project_builder.rebuild_and_run_all_tests_with_coverage()

    def ci_install_all(self, prefix: Path = None) -> None:
        """
        [CI] Install all project artifacts
        :param prefix: Specify the prefix path
        """
        self.project_builder.install_project(prefix)

    def ci_remove_conan_packages(self) -> None:
        """
        [CI] Remove all packages from Conan's local cache
        """
        self.project_builder.conan_remove_all()

    def ci_entry_point(self, args: argparse.Namespace, unknown_args: list[str]) -> int:
        """
        [CI] Main Entry Point of the Continuous Integration
        :param args: The parsed command line arguments
        :param unknown_args: The unknown command line arguments
        :return: The status code to be passed to `main()`.
        """
        try:
            if args.install_tools is True:
                self.ci_install_tools()
            elif args.install_toolchain is not None:
                self.ci_install_toolchain(*args.install_toolchain)
            elif args.select_toolchain is not None:
                self.ci_select_toolchain(*args.select_toolchain)
            elif args.restore_toolchain is not None:
                self.ci_install_toolchain(*args.restore_toolchain)
            elif args.build_all is not None:
                self.ci_build_all(*args.build_all, cmake_generate_flags=unknown_args or None)
            elif args.run_tests is not None:
                self.ci_run_tests(*args.run_tests)
            elif args.run_tests_with_coverage is True:
                self.ci_run_tests_with_coverage()
            elif args.install_all is not None:
                self.ci_install_all(None if args.install_all == "" else args.install_all)
            elif args.remove_packages is True:
                self.ci_remove_conan_packages()
            else:
                print(f"Unrecognized Chaos command: {args.command}.")
                raise ValueError
            return 0
        except (KeyError, ValueError, CalledProcessError):
            print("Failed to perform the CI operation.")
            traceback.print_exc()
            return -1

    #
    # MARK: Local Bootstrapping
    #

    def bootstrapping_create_ramdisk(self, mount_point: Path, size: int) -> None:
        sectors = size * 1024 * 1024 * 1024 / 512
        device = subprocess.check_output(["hdiutil", "attach", "-nomount", f"ram://{sectors}"], text=True).strip()
        subprocess.run(["newfs_hfs", "-v", mount_point.stem, device]).check_returncode()
        subprocess.run(["diskutil", "mount", "nobrowse", "-mountPoint", mount_point, device]).check_returncode()

    def bootstrapping_conan_install(self, build_directory: Path, profile: ConanProfile) -> None:
        # TODO: Refactor this
        profile_path = Path.cwd() / self.toolchain_manager.conan_profiles_folder_name / profile.filename
        conan_args = ["conan",
                      "install", Path.cwd(),
                      "--output-folder", build_directory,
                      "--update",
                      "--build", "missing",
                      "--profile:build", profile_path,
                      "--profile:host", profile_path]
        if self.project_builder.project.conan_flags is not None:
            conan_args.extend(self.project_builder.project.conan_flags)
        subprocess.run(conan_args).check_returncode()

    def bootstrapping_clion_local(self, toolchain_name: str, with_coverage: bool = False, size: int = 8) -> None:
        profile_dbg = ConanProfile(toolchain_name + "_Debug.conanprofile")
        profile_rel = ConanProfile(toolchain_name + "_Release.conanprofile")
        compiler = profile_dbg.identifier.compiler
        clion_toolchain_name = f"{compiler.type.value.lower()}-{compiler.version}-native"
        clion_build_directories_with_profiles: dict[Path, ConanProfile] = {
            Path.cwd() / f"cmake-build-debug-{clion_toolchain_name}": profile_dbg,
            Path.cwd() / f"cmake-build-release-{clion_toolchain_name}": profile_rel,
        }
        if with_coverage:
            clion_build_directories_with_profiles[Path.cwd() / f"cmake-build-debug-{clion_toolchain_name}-coverage"] = profile_dbg
            clion_build_directories_with_profiles[Path.cwd() / f"cmake-build-release-{clion_toolchain_name}-coverage"] = profile_rel
        for build_directory, profile in clion_build_directories_with_profiles.items():
            print("Bootstrapping CLion for Local Development...")
            print(f"    - Build Directory: {build_directory}")
            print(f"    - Conan Profile: {profile}")
            remove_folder_if_exists(build_directory)
            os.mkdir(build_directory)
            self.bootstrapping_create_ramdisk(build_directory, size)
            self.bootstrapping_conan_install(build_directory, profile)

    def bootstrapping_clion_interactive(self) -> None:
        self.clear_console()

        print("Please select a toolchain: \n")
        toolchains = self.toolchain_manager.fetch_compatible_compiler_toolchains_as_map(self.toolchain_manager.cmake_toolchains_folder_name)
        identifiers = sorted(list(toolchains.keys()))
        for index, identifier in enumerate(identifiers):
            print("[{:02}] {}".format(index, toolchains[identifier]))
        print()
        toolchain_index = int(input("Please enter the toolchain index: "))
        toolchain_name = Path(toolchains[identifiers[toolchain_index]].filename).stem

        print()
        with_coverage_input = input("Do you want to create build directories for coverage as well (Y/N, Default: Y): ").strip()
        with_coverage = True if not with_coverage_input else with_coverage_input == "Y"

        print()
        ramdisk_size_input = input("Please enter the ramdisk size: (Unit: GB, Default: 8 GB)").strip()
        ramdisk_size = 8 if not ramdisk_size_input else int(ramdisk_size_input)

        print()
        print("Bootstrapping CLion for Local Development:")
        print(f"    - Toolchain Name: {toolchain_name}")
        print(f"    - With Coverage: {with_coverage}")
        print(f"    - Ramdisk Size: {ramdisk_size} GB")
        print()
        self.bootstrapping_clion_local(toolchain_name, with_coverage, ramdisk_size)

    def cleanup_build_directories_for_clion(self) -> None:
        build_directories = [Path(entry.path) for entry in os.scandir(Path.cwd())
                             if entry.name.startswith("cmake-build") and Path(entry.path).is_mount()]
        for build_directory in build_directories:
            print(f"Ejecting the build directory {build_directory.name}...")
            subprocess.run(["diskutil", "eject", build_directory]).check_returncode()
            shutil.rmtree(build_directory)

    #
    # MARK: Create Menus
    #

    def create_compiler_menu(self) -> Menu:
        """
        Create a menu for installing compilers
        :return: The compiler menu
        """
        menu = Menu(">> Select a compiler you want to install")
        menu.add_item("GCC 10", self.toolchain_manager.install_gcc_10)
        menu.add_item("GCC 11", self.toolchain_manager.install_gcc_11)
        menu.add_item("GCC 12", self.toolchain_manager.install_gcc_12)
        menu.add_item("GCC 13", self.toolchain_manager.install_gcc_13)
        menu.add_item("GCC 14", self.toolchain_manager.install_gcc_14)
        menu.add_item("GCC 15", self.toolchain_manager.install_gcc_15)
        menu.add_item("Clang 13", self.toolchain_manager.install_clang_13)
        menu.add_item("Clang 14", self.toolchain_manager.install_clang_14)
        menu.add_item("Clang 15", self.toolchain_manager.install_clang_15)
        menu.add_item("Clang 16", self.toolchain_manager.install_clang_16)
        menu.add_item("Clang 17", self.toolchain_manager.install_clang_17)
        menu.add_item("Clang 18", self.toolchain_manager.install_clang_18)
        menu.add_item("Clang 19", self.toolchain_manager.install_clang_19)
        menu.add_item("Clang 20", self.toolchain_manager.install_clang_20)
        return menu

    def create_main_menu(self) -> Menu:
        """
        Create the main menu for the Chaos Control Center
        :return: The main menu
        """
        title = "===============================\n"
        title += "Welcome to Chaos Control Center\n"
        title += "What can I help you today?\n"
        title += "==============================="
        menu = Menu(title)
        menu.add_item(">> Configure Development Environment")
        menu.add_separator()
        menu.add_item("Install Build Essentials, CMake and Conan Package Manager", self.configurator.install_basic)
        menu.add_item("Install additional required development tools", self.configurator.install_other)
        menu.add_item("Install all required development tools", self.configurator.install_all)
        menu.add_separator()
        menu.add_item(">> Manage Compiler Toolchains")
        menu.add_separator()
        menu.add_submenu("Install a supported compiler", self.create_compiler_menu(), Menu.interact)
        menu.add_item("Install all supported compilers", self.toolchain_manager.install_all_compilers)
        menu.add_item("Select a compiler toolchain", self.toolchain_manager.select_compiler_toolchain)
        menu.add_separator()
        menu.add_item(">> Build, Test & Clean Projects")
        menu.add_separator()
        menu.add_item("Rebuild the project (DEBUG)", self.project_builder.rebuild_project_debug)
        menu.add_item("Rebuild the project (RELEASE)", self.project_builder.rebuild_project_release)
        menu.add_item("Rebuild and run all tests (DEBUG)", self.project_builder.rebuild_and_run_all_tests_debug)
        menu.add_item("Rebuild and run all tests (RELEASE)", self.project_builder.rebuild_and_run_all_tests_release)
        menu.add_item("Rebuild and run all tests with coverage", self.project_builder.rebuild_and_run_all_tests_with_coverage)
        menu.add_item("Clean the build folder", self.project_builder.clean_build_folder)
        menu.add_item("Clean the build folder and reset the toolchain", self.project_builder.clean_all)
        menu.add_item("Remove all Conan packages", self.project_builder.conan_remove_all)
        menu.add_item("Determine the minimum CMake version", self.project_builder.determine_minimum_cmake_version_interactive)
        menu.add_item("Bootstrap build directories for CLion (macOS)", self.bootstrapping_clion_interactive)
        menu.add_item("Clean build directories for CLion (macOS)", self.cleanup_build_directories_for_clion)
        return menu

    #
    # MARK: Chaos Running in Control Mode
    #

    def control(self, option: int = -1) -> int:
        """
        [CC] The main entry point of the Chaos Control Center
        :param option: Pass `-1` to enter interactive mode, otherwise a valid index to perform an operation
        :return: The status code to be passed to `main()`.
        """
        menu = self.create_main_menu()
        try:
            if option >= 0:
                menu.build_index_map()
                menu.select(option)
            else:
                Menu.interact(menu)
            return 0
        except (KeyError, ValueError, CalledProcessError):
            print("The Chaos Control Center has terminated unexpectedly.")
            traceback.print_exc()
            return -1


def required_length(min_nargs: int, max_nargs: int) -> Type[argparse.Action]:
    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if not min_nargs <= len(values) <= max_nargs:
                raise argparse.ArgumentTypeError(f"{self.dest} requires between {min_nargs} and {max_nargs} arguments.")
            setattr(args, self.dest, values)
    return RequiredLength

def main(project: Project) -> int:
    # Create the chaos control center
    chaos = Chaos(project)

    # Guard: Check whether users want to run the control center in interactive mode
    if len(sys.argv) == 1:
        return chaos.control()

    # Create the top-level parser
    parser = argparse.ArgumentParser(description="A control center for CMake + Conan + C++20 (and later) projects")

    # Add a mutually exclusive group for commands
    group = parser.add_mutually_exclusive_group()

    # Chaos Command: --install-tools
    group.add_argument("--install-tools",
                       action="store_true",
                       help="Install all required development tools")

    # Chaos Command: --install-toolchain <ToolchainName>
    group.add_argument("--install-toolchain",
                       nargs=1,
                       metavar="NAME",
                       help="Install a compiler toolchain named <NAME>")

    # Chaos Command: --select-toolchain <BuildToolchainName> [<HostToolchainName>]
    group.add_argument("--select-toolchain",
                       nargs="+",
                       metavar=("BUILD_NAME", "HOST_NAME"),
                       action=required_length(1, 2),
                       help="Select a compiler toolchain named <BUILD_NAME> that specifies the build environment " \
                       "and an optional compiler toolchain named <HOST_NAME> that specifies the host environment")

    # Chaos Command: --restore <Name>
    group.add_argument("--restore-toolchain",
                       nargs=1,
                       metavar="NAME",
                       help="Restore a compiler toolchain named <NAME>")

    # Chaos Command: --build-all <BuildType>
    group.add_argument("--build-all",
                       nargs=1,
                       metavar="TYPE",
                       choices=["Debug", "Release"],
                       help="Build all targets in Debug or Release mode")

    # Chaos Command: --run-tests <BuildType>
    group.add_argument("--run-tests",
                       nargs=1,
                       metavar="TYPE",
                       choices=["Debug", "Release"],
                       help="Run all tests in Debug or Release mode")

    # Chaos Command: -run-tests-with-coverage [<BuildType>]
    group.add_argument("--run-tests-with-coverage",
                       action="store_true",
                       help="Run all tests and analyze code coverage")

    # Chaos Command: --install-all <Path>
    group.add_argument("--install-all",
                       nargs="?",
                       const="",
                       default=None,
                       metavar="PATH",
                       help="Install all targets using the default prefix path or [PATH] if specified")

    # Chaos Command: --remove-packages
    group.add_argument("--remove-packages",
                       action="store_true",
                       help="Remove all packages from Conan's local cache")

    # Parse arguments
    return chaos.ci_entry_point(*parser.parse_known_args())
