#
# MARK: - Chaos Control Center
#

from __future__ import annotations
from subprocess import CalledProcessError
from typing import Type
from pathlib import Path
import argparse
import distro
import subprocess
import tempfile
import traceback
import platform
import shutil
import sys
import os

from .CompilerToolchainInstaller import (
    UnsupportedToolchainError,
    kSupportedGccVersions,
    kSupportedClangVersions,
    kSupportedAppleClangVersions
)
from .EnvironmentConfigurator import (
    EnvironmentConfiguratorMacOS,
    EnvironmentConfiguratorUbuntu,
    EnvironmentConfiguratorWindows,
    EnvironmentConfiguratorFreeBSD
)
from .CompilerToolchainInstaller import (
    CompilerToolchainInstallerMacOS,
    CompilerToolchainInstallerUbuntu2404,
    CompilerToolchainInstallerFreeBSD,
    CompilerToolchainInstallerUnsupported
)

from .Project import Project
from .ProjectBuilder import ProjectBuilder
from .CMake import CMake
from .Conan import Conan
from .CMakeManager import CMakeManagerMacOS, CMakeManagerLinux, CMakeManagerWindows, CMakeManagerUnsupported
from .CMakeToolchainDirectory import CMakeToolchainDirectory
from .ConanProfileDirectory import ConanProfileDirectory
from .BuildSystemDescriptor import BuildType, CMakeToolchain, ConanProfile, ConanProfilePair, HostSystem, Architecture
from .Menu import Menu
from .Utilities import remove_folder_if_exists


class Chaos:
    def __init__(self, project: Project):
        """
        Initialize the Chaos Control Center for the given project
        :param project: A project whose chaos to be controlled
        """
        self.project = project
        self.project_builder = ProjectBuilder(project, CMake.default(), Conan.default())
        self.cmake_toolchain_directory = CMakeToolchainDirectory(project.cmake_toolchains_directory)
        self.conan_profile_directory = ConanProfileDirectory(project.conan_profiles_directory)

        # Examine the current platform
        system = platform.system()
        machine = platform.machine()
        if system == "Darwin":
            self.host_system = HostSystem.kMacOS
            self.architecture = Architecture.kx86_64 if machine == "x86_64" else Architecture.kARM64
            self.configurator = EnvironmentConfiguratorMacOS(project.additional_tools_installer.macos)
            self.toolchain_installer = CompilerToolchainInstallerMacOS(self.architecture)
            self.cmake_manager = CMakeManagerMacOS()
        elif system == "Linux":
            distribution = distro.id()
            version = distro.version()
            if distribution == "ubuntu":
                self.host_system = HostSystem.kUbuntu
                self.architecture = Architecture.kx86_64
                self.configurator = EnvironmentConfiguratorUbuntu(project.additional_tools_installer.ubuntu)
                if version == "24.04":
                    self.toolchain_installer = CompilerToolchainInstallerUbuntu2404(Architecture.kx86_64)
                else:
                    print(f"Ubuntu {version} is not supported.")
                    raise EnvironmentError
                self.cmake_manager = CMakeManagerLinux()
            else:
                print(f"{distro.name(True)} is not supported.")
                raise EnvironmentError
        elif system == "Windows":
            self.host_system = HostSystem.kWindows
            self.architecture = Architecture.kx86_64
            self.configurator = EnvironmentConfiguratorWindows(project.additional_tools_installer.windows)
            self.toolchain_installer = CompilerToolchainInstallerUnsupported(HostSystem.kWindows, Architecture.kx86_64)
            self.cmake_manager = CMakeManagerWindows()
        elif system == "FreeBSD":
            self.host_system = HostSystem.kFreeBSD
            self.architecture = Architecture.kx86_64
            self.configurator = EnvironmentConfiguratorFreeBSD(project.additional_tools_installer.freebsd)
            self.toolchain_installer = CompilerToolchainInstallerFreeBSD(Architecture.kx86_64)
            self.cmake_manager = CMakeManagerUnsupported()
        else:
            print(f"{system} is not supported.")
            raise EnvironmentError

    #
    # MARK: Select Compiler Toolchains
    #

    def apply_compiler_toolchain(self,
                                 toolchain: CMakeToolchain,
                                 build_profiles: ConanProfilePair,
                                 host_profiles: ConanProfilePair) -> None:
        """
        [Action] Apply the given CMake toolchain and the given Conan profile pairs
        :param toolchain: The CMake toolchain to apply
        :param build_profiles: The Conan profile pair that specifies the build environment
        :param host_profiles: The Conan profile pair that specifies the host environment
        """
        print("Applying the CMake toolchain:", toolchain.filename)
        print("Applying the Conan build profile (Debug):", build_profiles.debug.filename)
        print("Applying the Conan build profile (Release):", build_profiles.release.filename)
        print("Applying the Conan host profile (Debug):", host_profiles.debug.filename)
        print("Applying the Conan host profile (Release):", host_profiles.release.filename)
        self.cmake_toolchain_directory.select(toolchain, self.project.current_toolchain_link_path)
        self.conan_profile_directory.select(build_profiles.debug, self.project.current_build_profile_debug_link_path)
        self.conan_profile_directory.select(build_profiles.release, self.project.current_build_profile_release_link_path)
        self.conan_profile_directory.select(host_profiles.debug, self.project.current_host_profile_debug_link_path)
        self.conan_profile_directory.select(host_profiles.release, self.project.current_host_profile_release_link_path)
        print()
        print("The CMake toolchain and the corresponding Conan profiles are both set.")

    def select_compiler_toolchain(self) -> None:
        """
        [Action] Prompt the user to select a compatible compiler toolchain and apply it
        """
        toolchains = self.cmake_toolchain_directory.fetch_compatible_as_map(self.host_system, self.architecture)
        profiles = self.conan_profile_directory.fetch_compatible_as_map(self.host_system, self.architecture)
        # Silently intersect: only identifiers that have both a toolchain and a complete profile pair
        identifiers = sorted(toolchains.keys() & profiles.keys(), key=lambda x: x.compiler)
        if not identifiers:
            print("No compatible compiler toolchain with matching Conan profiles is available.")
            return

        menu = Menu(">> Select a compiler toolchain")
        menu.add_item("      Arch       Compiler      Stdlib    Host OS   Distribution")
        menu.add_separator()
        for identifier in identifiers:
            label = "  {:>6}  {:^14}  {:^9}  {:^7}  {:^14}".format(
                identifier.architecture.value,
                str(identifier.compiler),
                identifier.standard_library.value,
                identifier.host_system.value,
                identifier.installation_source.value,
            )
            toolchain = toolchains[identifier]
            pair = profiles[identifier]
            menu.add_item(label, lambda t=toolchain, p=pair: self.apply_compiler_toolchain(t, p, p))
        Menu.interact(menu)

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
        :param name: The toolchain name (e.g., `gcc-14`, `clang-19`, `apple-clang-17`)
        :raise KeyError: if the given name is not a recognized compiler toolchain.
        :raise UnsupportedToolchainError: if the compiler is not supported on the current host system.
        :raise CalledProcessError: if failed to install the compiler.
        """
        tokens = name.rsplit("-", 1)
        if len(tokens) != 2 or not tokens[1].isdigit():
            raise KeyError(f"{name} is not a valid compiler toolchain.")
        family, version = tokens[0], int(tokens[1])
        match family:
            case "gcc":
                self.toolchain_installer.install_gcc(version)
            case "clang":
                self.toolchain_installer.install_clang(version)
            case "apple-clang":
                self.toolchain_installer.install_apple_clang(version)
            case _:
                raise KeyError(f"{name} is not a valid compiler toolchain.")

    def ci_select_toolchain(self, build_name: str, host_name: str = None) -> None:
        """
        [CI] Select the toolchain that has the given name
        :param build_name: The name of the toolchain that specifies the build environment
        :param host_name: The name of the toolchain that specifies the host environment
        :raise FileNotFoundError: if the given toolchain or profile name does not exist;
        :raise ValueError: if the given name is malformed;
        :raise CalledProcessError: if failed to select the toolchain.
        """
        toolchain = self.cmake_toolchain_directory.find(build_name)
        build_profiles = self.conan_profile_directory.find(build_name)
        host_profiles = self.conan_profile_directory.find(host_name) if host_name else build_profiles
        self.apply_compiler_toolchain(toolchain, build_profiles, host_profiles)

    def ci_restore_toolchain(self, name: str) -> None:
        """
        [CI] Restore the toolchain that has the given name (macOS only)
        :param name: The toolchain name (e.g., `apple-clang-17`)
        :raise KeyError: if the given name is not a recognized compiler toolchain.
        :raise KeyError: if the given name is not a valid Apple Clang compiler toolchain.
        :raise UnsupportedToolchainError: if the compiler is not supported on the current host system.
        :raise CalledProcessError: if failed to install the compiler.
        """
        tokens = name.rsplit("-", 1)
        if len(tokens) != 2 or not tokens[1].isdigit():
            raise KeyError(f"{name} is not a valid compiler toolchain.")
        family, version = tokens[0], int(tokens[1])
        match family:
            case "apple-clang":
                self.toolchain_installer.install_apple_clang(version)
            case _:
                raise KeyError(f"{name} is not a valid Apple Clang compiler toolchain.")

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
        self.project_builder.remove_all_packages()

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
                self.ci_restore_toolchain(*args.restore_toolchain)
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
        except (KeyError, ValueError, CalledProcessError, UnsupportedToolchainError):
            print("Failed to perform the CI operation.")
            traceback.print_exc()
            return -1

    #
    # MARK: Local Bootstrapping
    #

    def bootstrapping_create_ramdisk(self, mount_point: Path, size: int) -> None:
        """
        [Helper] Create and mount an HFS+ ramdisk of the given size at the given mount point (macOS only)
        :param mount_point: The path at which to mount the ramdisk
        :param size: The size of the ramdisk in gigabytes
        :raise CalledProcessError: if any of `hdiutil`, `newfs_hfs`, or `diskutil` exits with a non-zero status code.
        """
        sectors = size * 1024 * 1024 * 1024 // 512
        device = subprocess.check_output(["hdiutil", "attach", "-nomount", f"ram://{sectors}"], text=True).strip()
        subprocess.run(["newfs_hfs", "-v", mount_point.stem, device]).check_returncode()
        subprocess.run(["diskutil", "mount", "nobrowse", "-mountPoint", mount_point, device]).check_returncode()

    def bootstrapping_conan_install(self, build_directory: Path, profile: ConanProfile) -> None:
        """
        [Helper] Invoke `conan install` using the given profile, outputting to the given build directory
        :param build_directory: The output folder for the Conan-generated files
        :param profile: The Conan profile (used for both build and host)
        :raise CalledProcessError: if `conan install` exits with a non-zero status code.
        """
        profile_path = self.conan_profile_directory.path / profile.filename
        self.project_builder.conan.install(
            source_directory=self.project.source_directory,
            output_directory=build_directory,
            build_profile=profile_path,
            host_profile=profile_path,
            extra_args=self.project.conan_flags,
        )

    def bootstrapping_clion_local(self,
                                  toolchain: CMakeToolchain,
                                  profile_pair: ConanProfilePair,
                                  with_coverage: bool = False,
                                  size: int = 8) -> None:
        """
        [Helper] Create and populate CLion build directories for the given toolchain and profile pair
        :param toolchain: The CMake toolchain selected for CLion
        :param profile_pair: The Conan profile pair corresponding to the toolchain
        :param with_coverage: Pass `True` to also create coverage-enabled build directories
        :param size: The size of each ramdisk in gigabytes
        :raise CalledProcessError: if any of the underlying `hdiutil`/`diskutil`/`conan` calls fails.
        """
        compiler = toolchain.identifier.compiler
        clion_toolchain_name = f"{compiler.type.value.lower()}-{compiler.version}-native"
        build_directories_with_profiles: dict[Path, ConanProfile] = {
            self.project.source_directory / f"cmake-build-debug-{clion_toolchain_name}": profile_pair.debug,
            self.project.source_directory / f"cmake-build-release-{clion_toolchain_name}": profile_pair.release,
        }
        if with_coverage:
            build_directories_with_profiles[self.project.source_directory / f"cmake-build-debug-{clion_toolchain_name}-coverage"] = profile_pair.debug
            build_directories_with_profiles[self.project.source_directory / f"cmake-build-release-{clion_toolchain_name}-coverage"] = profile_pair.release
        for build_directory, profile in build_directories_with_profiles.items():
            print("Bootstrapping CLion for Local Development...")
            print(f"    - Build Directory: {build_directory}")
            print(f"    - Conan Profile: {profile}")
            remove_folder_if_exists(build_directory)
            os.mkdir(build_directory)
            self.bootstrapping_create_ramdisk(build_directory, size)
            self.bootstrapping_conan_install(build_directory, profile)

    def bootstrapping_clion_with_selection(self, toolchain: CMakeToolchain, profile_pair: ConanProfilePair) -> None:
        """
        [Helper] After the user selects a toolchain via `Menu`, prompt for the remaining options and run the bootstrap
        :param toolchain: The CMake toolchain selected by the user
        :param profile_pair: The Conan profile pair corresponding to the toolchain
        """
        print()
        with_coverage_input = input("Do you want to create build directories for coverage as well (Y/N, Default: Y): ").strip()
        with_coverage = True if not with_coverage_input else with_coverage_input == "Y"

        print()
        ramdisk_size_input = input("Please enter the ramdisk size: (Unit: GB, Default: 8 GB): ").strip()
        ramdisk_size = 8 if not ramdisk_size_input else int(ramdisk_size_input)

        print()
        print("Bootstrapping CLion for Local Development:")
        print(f"    - Compiler: {toolchain.identifier.compiler}")
        print(f"    - With Coverage: {with_coverage}")
        print(f"    - Ramdisk Size: {ramdisk_size} GB")
        print()
        self.bootstrapping_clion_local(toolchain, profile_pair, with_coverage, ramdisk_size)

    def bootstrapping_clion_interactive(self) -> None:
        """
        [Action] Prompt the user to select a compatible compiler toolchain, then bootstrap CLion build directories
        """
        toolchains = self.cmake_toolchain_directory.fetch_compatible_as_map(self.host_system, self.architecture)
        profiles = self.conan_profile_directory.fetch_compatible_as_map(self.host_system, self.architecture)
        identifiers = sorted(toolchains.keys() & profiles.keys(), key=lambda x: x.compiler)
        if not identifiers:
            print("No compatible compiler toolchain with matching Conan profiles is available.")
            return

        menu = Menu(">> Select a compiler toolchain for CLion")
        menu.add_item("      Arch       Compiler      Stdlib    Host OS   Distribution")
        menu.add_separator()
        for identifier in identifiers:
            label = "  {:>6}  {:^14}  {:^9}  {:^7}  {:^14}".format(
                identifier.architecture.value,
                str(identifier.compiler),
                identifier.standard_library.value,
                identifier.host_system.value,
                identifier.installation_source.value,
            )
            toolchain = toolchains[identifier]
            pair = profiles[identifier]
            menu.add_item(label, lambda t=toolchain, p=pair: self.bootstrapping_clion_with_selection(t, p))
        Menu.interact(menu)

    def cleanup_build_directories_for_clion(self) -> None:
        """
        [Action] Eject all CLion ramdisk-backed build directories and remove the corresponding folders
        :raise CalledProcessError: if `diskutil eject` fails on any of the build directories.
        """
        build_directories = [Path(entry.path) for entry in os.scandir(Path.cwd())
                             if entry.name.startswith("cmake-build") and Path(entry.path).is_mount()]
        for build_directory in build_directories:
            print(f"Ejecting the build directory {build_directory.name}...")
            subprocess.run(["diskutil", "eject", build_directory]).check_returncode()
            shutil.rmtree(build_directory)

    #
    # MARK: Determine Minimum CMake Version
    #

    def determine_minimum_cmake_version(self, min_major: int, min_minor: int, to_directory: Path) -> None:
        """
        [Helper] Determine the minimum version of CMake needed to configure the project
        :param min_major: The minimum major version of CMake from which to start the search
        :param min_minor: The minimum minor version of CMake from which to start the search
        :param to_directory: Path to the directory to store the extracted CMake binaries
        """
        results: dict[CMake, bool] = {}
        for cmake in self.cmake_manager.get_cmake_binaries(min_major, min_minor, to_directory, True):
            builder = ProjectBuilder(self.project, cmake, self.project_builder.conan)
            try:
                builder.configure(BuildType.kRelease)
                results[cmake] = True
            except CalledProcessError:
                results[cmake] = False
        print("\n\n")
        print("=====================")
        print("Summary of Execution:")
        print("=====================")
        for cmake, outcome in results.items():
            print(f"[{'SUCCESS' if outcome else 'FAILURE'}] CMake v{cmake.version}")

    def determine_minimum_cmake_version_interactive(self) -> None:
        """
        [Action] Determine the minimum version of CMake needed to configure the project
        """
        try:
            min_major = int(input("Enter the minimum major version of CMake to start the search: "))
            min_minor = int(input("Enter the minimum minor version of CMake to start the search: "))
            directory = input("Enter the path to the directory to store CMake binaries. "
                              "(Default: A Temporary Folder): ").strip()
            if not directory:
                with tempfile.TemporaryDirectory() as temp_directory:
                    self.determine_minimum_cmake_version(min_major, min_minor, Path(temp_directory))
            else:
                self.determine_minimum_cmake_version(min_major, min_minor, Path(directory))
        except ValueError:
            print("Invalid input. Please try again.")

    #
    # MARK: Create Menus
    #

    def create_compiler_menu(self) -> Menu:
        """
        Create a menu for installing compilers
        :return: The compiler menu
        """
        menu = Menu(">> Select a compiler you want to install")
        for version in kSupportedGccVersions:
            menu.add_item(f"GCC {version}", lambda v=version: self.toolchain_installer.install_gcc(v))
        for version in kSupportedClangVersions:
            menu.add_item(f"Clang {version}", lambda v=version: self.toolchain_installer.install_clang(v))
        for version in kSupportedAppleClangVersions:
            menu.add_item(f"AppleClang {version}", lambda v=version: self.toolchain_installer.install_apple_clang(v))
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
        if self.host_system != HostSystem.kWindows:
            menu.add_submenu("Install a supported compiler", self.create_compiler_menu(), Menu.interact)
            menu.add_item("Install all supported compilers", self.toolchain_installer.install_all_compilers)
        menu.add_item("Select a compiler toolchain", self.select_compiler_toolchain)
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
        menu.add_item("Remove all Conan packages", self.project_builder.remove_all_packages)
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
        except (KeyError, ValueError, CalledProcessError, UnsupportedToolchainError):
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

    # Chaos Command: --restore-toolchain <Name>
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
