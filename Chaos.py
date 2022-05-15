#
# MARK: - Chaos Control Center
#

import sys
import distro
import platform
from typing import Callable
from .EnvironmentConfigurator import *
from .ProjectBuilder import *


class Config:
    # Name of the binary that runs all tests
    test: str


class Chaos:
    environmentConfigurator: EnvironmentConfigurator
    compilerToolchainManager: CompilerToolchainManager
    projectBuilder: ProjectBuilder

    def __init__(self, config: Config):
        """
        Initialize the Chaos Control Center with the given configuration
        :param config: A configuration object
        """
        system = platform.system()
        machine = platform.machine()
        if system == "Darwin":
            self.environmentConfigurator = EnvironmentConfiguratorMacOS()
            self.compilerToolchainManager = CompilerToolchainManagerMacOS(Architecture.kx86_64 if machine == "x86_64" else Architecture.kARM64)
            self.projectBuilder = ProjectBuilder(config.test)
        elif system == "Linux":
            distribution = distro.id()
            version = distro.version()
            if distribution == "ubuntu":
                self.environmentConfigurator = EnvironmentConfiguratorUbuntu()
                if version == "20.04":
                    self.compilerToolchainManager = CompilerToolchainManagerUbuntu2004(Architecture.kx86_64)
                elif version == "22.04":
                    self.compilerToolchainManager = CompilerToolchainManagerUbuntu2204(Architecture.kx86_64)
                else:
                    print("Ubuntu {} is not tested.".format(version))
                    raise EnvironmentError
                self.projectBuilder = ProjectBuilder(config.test)
            else:
                print("{} is not supported.".format(distro.name(True)))
                raise EnvironmentError
        elif system == "Windows":
            self.environmentConfigurator = EnvironmentConfiguratorWindows()
            self.compilerToolchainManager = CompilerToolchainManagerWindows(Architecture.kx86_64)
            self.projectBuilder = ProjectBuilder(config.test)
        else:
            print("{} is not supported.".format(system))
            raise EnvironmentError

    def control(self, option: int) -> None:
        """
        Main entry point of the Chaos Control Center
        :param option: Pass `-1` to enter interactive mode, otherwise a valid index to perform an operation
        """
        actions: list[Callable[[], None]] = [
            self.environmentConfigurator.install_all,
            self.compilerToolchainManager.install_gcc_10,
            self.compilerToolchainManager.install_gcc_11,
            self.compilerToolchainManager.install_gcc_12,
            self.compilerToolchainManager.install_clang_13,
            self.compilerToolchainManager.install_clang_14,
            self.compilerToolchainManager.install_all_compilers,
            self.compilerToolchainManager.select_compiler_toolchain,
            self.compilerToolchainManager.generate_xcode_configuration,
            self.projectBuilder.rebuild_project_debug,
            self.projectBuilder.rebuild_project_release,
            self.projectBuilder.run_all_tests_debug,
            self.projectBuilder.run_all_tests_release,
            self.projectBuilder.clean_build_folder,
        ]
        if option >= 0:
            # Non-interactive mode
            actions[option]()
            return
        while True:
            os.system("clear")
            print()
            print("===============================")
            print("Welcome to Chaos Control Center")
            print("What can I help you today?     ")
            print("===============================")
            print()
            print(">> Configure Development Environment")
            print()
            print("[00] Install all required development tools.")
            print()
            print(">> Manage Compiler Toolchains")
            print()
            print("[01] Install GCC 10.")
            print("[02] Install GCC 11.")
            print("[03] Install GCC 12.")
            print("[04] Install Clang 13.")
            print("[05] Install Clang 14.")
            print("[06] Install all supported compilers.")
            print("[07] Select a compiler toolchain.")
            print("[08] Generate the Xcode configuration.")
            print()
            print(">> Build, Test & Clean Projects")
            print()
            print("[09] Rebuild the project (DEBUG).")
            print("[10] Rebuild the project (RELEASE).")
            print("[11] Run all tests (DEBUG).")
            print("[12] Run all tests (RELEASE).")
            print("[13] Clean the build folder.")
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


def main(config: Config) -> None:
    chaos = Chaos(config)
    option = -1
    if len(sys.argv) > 2:
        print("Usage:")
        print("{} <option> to run an action directly.", sys.argv[0])
        print("{} to enter interactive mode.", sys.argv[0])
    elif len(sys.argv) == 1:
        # Interactive mode
        pass
    else:
        # Action mode
        option = int(sys.argv[1])
    chaos.control(option)
