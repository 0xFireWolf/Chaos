#
# MARK: - Chaos Control Center
#

import sys
import distro
import traceback
from subprocess import CalledProcessError
from .EnvironmentConfigurator import *
from .ProjectBuilder import *


class Config:
    def __init__(self):
        self.tests: list[str] = []
        self.install_additional_tools_macos: Callable[[], None] = None
        self.install_additional_tools_ubuntu: Callable[[], None] = None
        self.install_additional_tools_windows: Callable[[], None] = None
        self.coverage_source_folder: Path = None
        self.coverage_exclude_patterns: list[str] = None


class Chaos:
    def __init__(self, config: Config):
        """
        Initialize the Chaos Control Center with the given configuration
        :param config: A configuration object
        """
        system = platform.system()
        machine = platform.machine()
        self.clearConsole = lambda: os.system("clear")
        if system == "Darwin":
            self.environmentConfigurator = EnvironmentConfiguratorMacOS(config.install_additional_tools_macos)
            self.compilerToolchainManager = CompilerToolchainManagerMacOS(Architecture.kx86_64 if machine == "x86_64" else Architecture.kARM64)
            self.projectBuilder = ProjectBuilder(config.tests, config.coverage_source_folder, config.coverage_exclude_patterns)
        elif system == "Linux":
            distribution = distro.id()
            version = distro.version()
            if distribution == "ubuntu":
                self.environmentConfigurator = EnvironmentConfiguratorUbuntu(config.install_additional_tools_ubuntu)
                if version == "20.04":
                    self.compilerToolchainManager = CompilerToolchainManagerUbuntu2004(Architecture.kx86_64)
                elif version == "22.04":
                    self.compilerToolchainManager = CompilerToolchainManagerUbuntu2204(Architecture.kx86_64)
                else:
                    print("Ubuntu {} is not tested.".format(version))
                    raise EnvironmentError
                self.projectBuilder = ProjectBuilder(config.tests, config.coverage_source_folder, config.coverage_exclude_patterns)
            else:
                print("{} is not supported.".format(distro.name(True)))
                raise EnvironmentError
        elif system == "Windows":
            self.environmentConfigurator = EnvironmentConfiguratorWindows(config.install_additional_tools_windows)
            self.compilerToolchainManager = CompilerToolchainManagerWindows(Architecture.kx86_64)
            self.projectBuilder = ProjectBuilder(config.tests, config.coverage_source_folder, config.coverage_exclude_patterns)
            self.clearConsole = lambda: os.system("cls")
        else:
            print("{} is not supported.".format(system))
            raise EnvironmentError

    def ci_install_toolchain(self, name: str) -> None:
        """
        [CI] Install the toolchain of the given name
        :param name: Name of the toolchain. Must be one of `gcc-10`, `gcc-11`, `gcc-12`, `clang-13` and `clang-14`
        :raise `KeyError` if the given name is invalid;
               `CalledProcessError` if failed to install the toolchain.
        """
        toolchains: dict[str, Callable[[], None]] = {
            "gcc-10": self.compilerToolchainManager.install_gcc_10,
            "gcc-11": self.compilerToolchainManager.install_gcc_11,
            "gcc-12": self.compilerToolchainManager.install_gcc_12,
            "clang-13": self.compilerToolchainManager.install_clang_13,
            "clang-14": self.compilerToolchainManager.install_clang_14,
            "clang-15": self.compilerToolchainManager.install_clang_15,
            "apple-clang-13": self.compilerToolchainManager.install_apple_clang_13,
            "apple-clang-14": self.compilerToolchainManager.install_apple_clang_14,
        }
        toolchains[name]()

    def ci_select_toolchain(self, name: str) -> None:
        """
        [CI] Select the toolchain of the given name
        :param name: Name of the toolchain
        :raise `ValueError` if the given toolchain name is invalid;
               `CalledProcessError` if failed to select the toolchain.
        """
        toolchain = Toolchain(name + ".cmake")
        profile_dbg = ConanProfile(name + "_Debug.conanprofile")
        profile_rel = ConanProfile(name + "_Release.conanprofile")
        self.compilerToolchainManager.apply_compiler_toolchain(toolchain, profile_dbg, profile_rel)

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
                self.ci_select_toolchain(sys.argv[3])
            elif command == "--build-all":
                self.ci_build_all(sys.argv[3])
            elif command == "--run-tests":
                self.ci_run_tests(sys.argv[3])
            elif command == "--run-tests-with-coverage":
                self.ci_run_tests_with_coverage()
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
            print("[06] Install Clang 13.")
            print("[07] Install Clang 14.")
            print("[08] Install Clang 15.")
            print("[09] Install all supported compilers.")
            print("[10] Select a compiler toolchain.")
            print("[11] Generate the Xcode configuration.")
            print()
            print(">> Build, Test & Clean Projects")
            print()
            print("[12] Rebuild the project (DEBUG).")
            print("[13] Rebuild the project (RELEASE).")
            print("[14] Rebuild and run all tests (DEBUG).")
            print("[15] Rebuild and run all tests (RELEASE).")
            print("[16] Rebuild and run all tests with coverage.")
            print("[17] Clean the build folder.")
            print("[18] Clean the build folder and reset the toolchain.")
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
            self.compilerToolchainManager.install_clang_13,
            self.compilerToolchainManager.install_clang_14,
            self.compilerToolchainManager.install_clang_15,
            self.compilerToolchainManager.install_all_compilers,
            self.compilerToolchainManager.select_compiler_toolchain,
            self.compilerToolchainManager.generate_xcode_configuration,
            self.projectBuilder.rebuild_project_debug,
            self.projectBuilder.rebuild_project_release,
            self.projectBuilder.rebuild_and_run_all_tests_debug,
            self.projectBuilder.rebuild_and_run_all_tests_release,
            self.projectBuilder.rebuild_and_run_all_tests_with_coverage,
            self.projectBuilder.clean_build_folder,
            self.projectBuilder.clean_all
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


def main(config: Config) -> int:
    chaos = Chaos(config)
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
