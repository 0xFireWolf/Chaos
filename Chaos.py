#
# MARK: - Chaos Control Center
#
from __future__ import annotations
import sys
import distro
import traceback
from subprocess import CalledProcessError
from .EnvironmentConfigurator import *
from .ProjectBuilder import *
from .CMakeManager import CMakeManagerMacOS, CMakeManagerLinux, CMakeManagerWindows


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
            self.environmentConfigurator = EnvironmentConfiguratorMacOS(project.additional_tools_installer.macos)
            self.compilerToolchainManager = CompilerToolchainManagerMacOS(architecture)
            self.projectBuilder = ProjectBuilder(project, CMakeManagerMacOS())
            self.clearConsole = lambda: os.system("clear")
        elif system == "Linux":
            distribution = distro.id()
            version = distro.version()
            if distribution == "ubuntu":
                self.environmentConfigurator = EnvironmentConfiguratorUbuntu(project.additional_tools_installer.ubuntu)
                if version == "20.04":
                    self.compilerToolchainManager = CompilerToolchainManagerUbuntu2004(Architecture.kx86_64)
                elif version == "22.04":
                    self.compilerToolchainManager = CompilerToolchainManagerUbuntu2204(Architecture.kx86_64)
                else:
                    print("Ubuntu {} is not tested.".format(version))
                    raise EnvironmentError
                self.projectBuilder = ProjectBuilder(project, CMakeManagerLinux())
                self.clearConsole = lambda: os.system("clear")
            else:
                print("{} is not supported.".format(distro.name(True)))
                raise EnvironmentError
        elif system == "Windows":
            self.environmentConfigurator = EnvironmentConfiguratorWindows(project.additional_tools_installer.windows)
            self.compilerToolchainManager = CompilerToolchainManagerWindows(Architecture.kx86_64)
            self.projectBuilder = ProjectBuilder(project, CMakeManagerWindows())
            self.clearConsole = lambda: os.system("cls")
        elif system == "FreeBSD":
            self.environmentConfigurator = EnvironmentConfiguratorFreeBSD(project.additional_tools_installer.freebsd)
            self.compilerToolchainManager = CompilerToolchainManagerFreeBSD(Architecture.kx86_64)
            self.projectBuilder = ProjectBuilder(project, CMakeManager())  # CMakeManager does not support FreeBSD
            self.clearConsole = lambda: os.system("clear")
        else:
            print("{} is not supported.".format(system))
            raise EnvironmentError

    def ci_install_toolchain(self, name: str) -> None:
        """
        [CI] Install the toolchain that has the given name
        :param name: The toolchain name
        :raise `KeyError` if the given name is invalid;
               `CalledProcessError` if failed to install the toolchain.
        """
        toolchains: dict[str, Callable[[], None]] = {
            "gcc-10": self.compilerToolchainManager.install_gcc_10,
            "gcc-11": self.compilerToolchainManager.install_gcc_11,
            "gcc-12": self.compilerToolchainManager.install_gcc_12,
            "gcc-13": self.compilerToolchainManager.install_gcc_13,
            "clang-13": self.compilerToolchainManager.install_clang_13,
            "clang-14": self.compilerToolchainManager.install_clang_14,
            "clang-15": self.compilerToolchainManager.install_clang_15,
            "clang-16": self.compilerToolchainManager.install_clang_16,
            "clang-17": self.compilerToolchainManager.install_clang_17,
            "clang-18": self.compilerToolchainManager.install_clang_18,
            "apple-clang-13": self.compilerToolchainManager.install_apple_clang_13,
            "apple-clang-14": self.compilerToolchainManager.install_apple_clang_14,
            "apple-clang-15": self.compilerToolchainManager.install_apple_clang_15,
        }
        toolchains[name]()

    def ci_select_toolchain(self, build_name: str, host_name: str = None) -> None:
        """
        [CI] Select the toolchain that has the given name
        :param build_name: The name of the toolchain that specifies the build environment
        :param host_name: Te name of the toolchain that specifies the host environment
        :raise `ValueError` if the given toolchain name is invalid;
               `CalledProcessError` if failed to select the toolchain.
        """
        cmake_toolchain = Toolchain(build_name + ".cmake")
        build_profile_dbg = ConanProfile(build_name + "_Debug.conanprofile")
        build_profile_rel = ConanProfile(build_name + "_Release.conanprofile")
        host_profile_dbg = None if host_name is None else ConanProfile(host_name + "_Debug.conanprofile")
        host_profile_rel = None if host_name is None else ConanProfile(host_name + "_Release.conanprofile")
        self.compilerToolchainManager.apply_compiler_toolchain(cmake_toolchain,
                                                               build_profile_dbg, build_profile_rel,
                                                               host_profile_dbg, host_profile_rel)

    def ci_build_all(self, btype: str) -> None:
        """
        [CI] Build all targets
        :param btype: The raw build type
        :raise `ValueError` if the given build type is invalid;
               `CalledProcessError` if failed to build one of the targets.
        """
        self.projectBuilder.rebuild_project(BuildType(btype))

    def ci_run_tests(self, btype: str) -> None:
        """
        [CI] Run all tests
        :param btype: The raw build type
        :raise `ValueError` if the given build type is invalid;
               `CalledProcessError` if one of the tests has failed.
        """
        self.projectBuilder.run_all_tests(BuildType(btype))

    def ci_run_tests_with_coverage(self) -> None:
        """
        [CI] Run all tests and analyze code coverage
        :raise `CalledProcessError` if one of the tests has failed.
        """
        self.projectBuilder.rebuild_and_run_all_tests_with_coverage()

    def ci_install_all(self, prefix: Path = None) -> None:
        """
        [CI] Install all project artifacts
        :param prefix: Specify the prefix path
        """
        self.projectBuilder.install_project(prefix)

    def ci(self) -> int:
        """
        [CI] Main Entry Point of the Continuous Integration
        :return: The status code to be passed to `main()`.
        """
        command = sys.argv[2]
        result = 0
        try:
            if command == "--install-toolchain":
                self.ci_install_toolchain(sys.argv[3])
            elif command == "--select-toolchain":
                if len(sys.argv) == 4:
                    self.ci_select_toolchain(sys.argv[3])
                else:
                    self.ci_select_toolchain(sys.argv[3], sys.argv[4])
            elif command == "--restore-toolchain":
                self.ci_install_toolchain(sys.argv[3])
            elif command == "--build-all":
                self.ci_build_all(sys.argv[3])
            elif command == "--run-tests":
                self.ci_run_tests(sys.argv[3])
            elif command == "--run-tests-with-coverage":
                self.ci_run_tests_with_coverage()
            elif command == "--install-all":
                self.ci_install_all(sys.argv[3] if len(sys.argv) == 4 else None)
            else:
                print("Unrecognized Chaos command: {}.".format(command))
                raise ValueError
        except (KeyError, ValueError, CalledProcessError):
            print("Failed to perform the CI operation.")
            traceback.print_exc()
            result = -1
        return result

    def control_action_mode(self, actions: list[Callable[[], None]], option: int) -> None:
        """
        [CC] Chaos Control Center Action Mode
        :param actions: A list of available actions
        :param option: The index of the action to be performed
        :raise: `IndexError` if the given option is invalid;
                `CalledProcessError` if the action has failed.
        """
        if option not in range(0, len(actions)):
            print("The given option {} is invalid.".format(option))
            raise IndexError
        actions[option]()

    def control_interactive_mode(self, actions: list[Callable[[], None]]) -> None:
        """
        [CC] Chaos Control Center Interactive Mode
        :param actions: A list of available actions
        :return: The status code to be passed to `main()`.
        """
        while True:
            self.clearConsole()
            print()
            print("===============================")
            print("Welcome to Chaos Control Center")
            print("What can I help you today?     ")
            print("===============================")
            print()
            print(">> Configure Development Environment")
            print()
            print("[00] Install CMake, Ninja and Conan Package Manager.")
            print("[01] Install additional required development tools.")
            print("[02] Install all required development tools.")
            print()
            print(">> Manage Compiler Toolchains")
            print()
            print("[03] Install GCC 10.")
            print("[04] Install GCC 11.")
            print("[05] Install GCC 12.")
            print("[06] Install GCC 13.")
            print("[07] Install Clang 13.")
            print("[08] Install Clang 14.")
            print("[09] Install Clang 15.")
            print("[10] Install Clang 16.")
            print("[11] Install Clang 17.")
            print("[12] Install Clang 18.")
            print("[13] Install all supported compilers.")
            print("[14] Select a compiler toolchain.")
            print("[15] Generate the Xcode configuration.")
            print()
            print(">> Build, Test & Clean Projects")
            print()
            print("[16] Rebuild the project (DEBUG).")
            print("[17] Rebuild the project (RELEASE).")
            print("[18] Rebuild and run all tests (DEBUG).")
            print("[19] Rebuild and run all tests (RELEASE).")
            print("[20] Rebuild and run all tests with coverage.")
            print("[21] Clean the build folder.")
            print("[22] Clean the build folder and reset the toolchain.")
            print("[23] Determine the minimum CMake version.")
            print()
            print("Press Ctrl-C or Ctrl-D to exit the menu.")
            option = 0
            try:
                option = int(input("Input the number and press ENTER: "))
                if option not in range(0, len(actions)):
                    raise IndexError
            except ValueError:
                print("Not a number! Please try again.")
                continue
            except IndexError:
                print("The option number {} is invalid.", option)
                continue
            except (KeyboardInterrupt, EOFError):
                print("Goodbye.")
                break
            actions[option]()
            input("\nPress a key to continue...")

    def control(self, option: int) -> int:
        """
        [CC] Main entry point of the Chaos Control Center
        :param option: Pass `-1` to enter interactive mode, otherwise a valid index to perform an operation
        :return: The status code to be passed to `main()`.
        """
        actions: list[Callable[[], None]] = [
            self.environmentConfigurator.install_basic,
            self.environmentConfigurator.install_other,
            self.environmentConfigurator.install_all,
            self.compilerToolchainManager.install_gcc_10,
            self.compilerToolchainManager.install_gcc_11,
            self.compilerToolchainManager.install_gcc_12,
            self.compilerToolchainManager.install_gcc_13,
            self.compilerToolchainManager.install_clang_13,
            self.compilerToolchainManager.install_clang_14,
            self.compilerToolchainManager.install_clang_15,
            self.compilerToolchainManager.install_clang_16,
            self.compilerToolchainManager.install_clang_17,
            self.compilerToolchainManager.install_clang_18,
            self.compilerToolchainManager.install_all_compilers,
            self.compilerToolchainManager.select_compiler_toolchain,
            self.compilerToolchainManager.generate_xcode_configuration,
            self.projectBuilder.rebuild_project_debug,
            self.projectBuilder.rebuild_project_release,
            self.projectBuilder.rebuild_and_run_all_tests_debug,
            self.projectBuilder.rebuild_and_run_all_tests_release,
            self.projectBuilder.rebuild_and_run_all_tests_with_coverage,
            self.projectBuilder.clean_build_folder,
            self.projectBuilder.clean_all,
            self.projectBuilder.determine_minimum_cmake_version_interactive,
        ]
        result = 0
        try:
            if option >= 0:
                self.control_action_mode(actions, option)
            else:
                self.control_interactive_mode(actions)
        except (IndexError, ValueError, CalledProcessError):
            print("The Chaos Control Center has terminated unexpectedly.")
            traceback.print_exc()
            result = -1
        return result


def main(project: Project) -> int:
    chaos = Chaos(project)
    # Default: Interactive mode
    option = -1

    if len(sys.argv) > 2:
        if sys.argv[1] == "chaos":
            # CI mode
            return chaos.ci()
        else:
            print("Usage:")
            print("{} to enter interactive mode.", sys.argv[0])
            print("{} <option> to run an action directly.", sys.argv[0])
            print("{} chaos <command> <args>... to run the script in CI mode.", sys.argv[0])
            return -1

    if len(sys.argv) == 2:
        # Action mode
        try:
            option = int(sys.argv[1])
        except ValueError:
            print("The option value must be an integer.")
            return -1

    return chaos.control(option)
