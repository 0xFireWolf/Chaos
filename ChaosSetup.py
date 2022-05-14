#
# MARK: - Chaos Setup
#
from typing import Callable

import distro
import platform
from .EnvironmentConfigurator import *
from .ProjectBuilder import *


class ChaosConfig:
    # Name of the binary that runs all tests
    test: str


class ChaosSetup:
    environmentConfigurator: EnvironmentConfigurator
    compilerToolchainManager: CompilerToolchainManager
    projectBuilder: ProjectBuilder

    def __init__(self, config: ChaosConfig):
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


def main(config: ChaosConfig, option: int) -> None:
    setup = ChaosSetup(config)
    actions: list[Callable[[], None]] = [
        setup.environmentConfigurator.install_all,
        setup.compilerToolchainManager.install_gcc_10,
        setup.compilerToolchainManager.install_gcc_11,
        setup.compilerToolchainManager.install_gcc_12,
        setup.compilerToolchainManager.install_clang_13,
        setup.compilerToolchainManager.install_clang_14,
        setup.compilerToolchainManager.install_all_compilers,
        setup.compilerToolchainManager.select_compiler_toolchain,
        setup.compilerToolchainManager.generate_xcode_configuration,
        setup.projectBuilder.rebuild_project_debug,
        setup.projectBuilder.rebuild_project_release,
        setup.projectBuilder.run_all_tests_debug,
        setup.projectBuilder.run_all_tests_release,
        setup.projectBuilder.clean_build_folder,
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
