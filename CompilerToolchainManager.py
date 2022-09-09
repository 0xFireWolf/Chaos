#
# MARK: - Manage Compiler Toolchains
#

import shutil
import tempfile
import pathlib
from .BuildSystemDescriptor import *
from .Utilities import *

kCurrentToolchainFile = "CurrentToolchain.cmake"
kCurrentConanProfileDebug = "CurrentProfileDebug.conanprofile"
kCurrentConanProfileRelease = "CurrentProfileRelease.conanprofile"
kXcodeConfigFile = "conanbuildinfo.xcconfig"
kXcodeConfigFileDebug = "conanbuildinfo.debug.xcconfig"
kXcodeConfigFileRelease = "conanbuildinfo.release.xcconfig"


# An abstract manager that sets up the compiler toolchain on the host system
class CompilerToolchainManager:
    def __init__(self, host: HostSystem, architecture: Architecture):
        # Filter out toolchains that run on a different host system
        self.hostSystem = host
        # Filter out toolchains that have a different architecture
        self.architecture = architecture

    def install_gcc_10(self) -> None:
        raise NotImplementedError

    def install_gcc_11(self) -> None:
        raise NotImplementedError

    def install_gcc_12(self) -> None:
        raise NotImplementedError

    def install_clang_13(self) -> None:
        raise NotImplementedError

    def install_clang_14(self) -> None:
        raise NotImplementedError

    def install_clang_15(self) -> None:
        raise NotImplementedError

    def install_all_compilers(self) -> None:
        self.install_gcc_10()
        self.install_gcc_11()
        self.install_gcc_12()
        self.install_clang_13()
        self.install_clang_14()
        self.install_clang_15()

    def fetch_all_conan_profiles(self, folder: str) -> list[ConanProfile]:
        """
        [Helper] Fetch all conan profiles at the given folder
        :param folder: Path to the folder that stores conan profiles
        :return: A list of parsed conan profiles.
        :raise: `ValueError` if failed to parse one of the profiles in the given folder.
        """
        return [ConanProfile(filename)
                for filename in filter(lambda filename: filename.endswith(".conanprofile"), os.listdir(folder))]

    def fetch_compatible_conan_profiles(self, folder: str) -> list[ConanProfile]:
        """
        [Helper] Fetch all conan profiles compatible with the current host system at the given folder
        :param folder: Path to the folder that stores conan profiles
        :return: A list of parsed conan profiles.
        :raise: `ValueError` if failed to parse one of the profiles in the given folder.
        """
        return list(filter(lambda profile: profile.identifier.compatible(self.hostSystem, self.architecture),
                           self.fetch_all_conan_profiles(folder)))

    def fetch_compatible_conan_profiles_as_map(self, folder: str) -> (dict[BuildSystemIdentifier, ConanProfile], dict[BuildSystemIdentifier, ConanProfile]):
        """
        [Helper] Fetch all conan profiles compatible with the current host system at the given folder and build the profile map
        :param folder: Path to the folder that stores conan profiles
        :return: A map keyed by the profile identifier.
        :raise: `ValueError` if failed to parse one of the profiles in the given folder.
        """
        pmap_dbg: dict[BuildSystemIdentifier, ConanProfile] = {}
        pmap_rel: dict[BuildSystemIdentifier, ConanProfile] = {}
        profiles = self.fetch_compatible_conan_profiles(folder)
        for profile in profiles:
            if profile.buildType == BuildType.kDebug:
                pmap_dbg[profile.identifier] = profile
            else:
                pmap_rel[profile.identifier] = profile
        return pmap_dbg, pmap_rel

    def fetch_all_compiler_toolchains(self, folder: str) -> list[Toolchain]:
        """
        [Helper] Fetch all CMake compiler toolchains at the given folder
        :param folder: Path to the folder that stores CMake compiler toolchains
        :return: A list of parsed compiler toolchains.
        :raise: `ValueError` if failed to parse one of the toolchains in the given folder.
        """
        return [Toolchain(filename)
                for filename in filter(lambda filename: filename.endswith(".cmake"), os.listdir(folder))]

    def fetch_compatible_compiler_toolchains(self, folder: str) -> list[Toolchain]:
        """
        [Helper] Fetch all CMake compiler toolchains compatible with the current host system at the given folder
        :param folder: Path to the folder that stores CMake compiler toolchains
        :return: A list of parsed compiler toolchains.
        :raise: `ValueError` if failed to parse one of the toolchains in the given folder.
        """
        return list(filter(lambda toolchain: toolchain.identifier.compatible(self.hostSystem, self.architecture),
                           self.fetch_all_compiler_toolchains(folder)))

    def fetch_compatible_compiler_toolchains_as_map(self, folder: str) -> dict[BuildSystemIdentifier, Toolchain]:
        """
        [Helper] Fetch all CMake compiler toolchains compatible with the current host system at the given folder and build the toolchain map
        :param folder: Path to the folder that stores CMake compiler toolchains
        :return: A map keyed by the toolchain identifier.
        :raise: `ValueError` if failed to parse one of the toolchains in the given folder.
        """
        return {toolchain.identifier: toolchain for toolchain in self.fetch_compatible_compiler_toolchains(folder)}

    def apply_compiler_toolchain(self, toolchain: Toolchain, profileDebug: ConanProfile, profileRelease: ConanProfile) -> None:
        """
        [Action] [Helper] Apply the given combination of the compiler toolchain and the Conan profile
        :param toolchain: The compiler toolchain
        :param profileDebug: The Conan profile for debug build
        :param profileRelease: The Conan profile for release build
        """
        print("Applying the compiler toolchain:", toolchain.filename)
        print("Applying the Conan profile (Debug):", profileDebug.filename)
        print("Applying the Conan profile (Release):", profileRelease.filename)
        remove_file_if_exist(kCurrentToolchainFile)
        remove_file_if_exist(kCurrentConanProfileDebug)
        remove_file_if_exist(kCurrentConanProfileRelease)
        os.symlink(pathlib.Path("Toolchains/{}".format(toolchain.filename)), pathlib.Path(kCurrentToolchainFile))
        os.symlink(pathlib.Path("Profiles/{}".format(profileDebug.filename)), pathlib.Path(kCurrentConanProfileDebug))
        os.symlink(pathlib.Path("Profiles/{}".format(profileRelease.filename)), pathlib.Path(kCurrentConanProfileRelease))
        print()
        print("The toolchain and the corresponding Conan profiles are both set.")

    def select_compiler_toolchain(self) -> None:
        """
        [Action] Select a compiler toolchain
        """
        toolchains = self.fetch_compatible_compiler_toolchains_as_map("Toolchains")
        profiles_dbg, profiles_rel = self.fetch_compatible_conan_profiles_as_map("Profiles")
        assert len(toolchains.keys()) == len(profiles_dbg.keys())
        assert len(toolchains.keys()) == len(profiles_rel.keys())
        identifiers = sorted(list(toolchains.keys()))
        while True:
            print("\n>> Available Compiler Toolchains:\n")
            print("\t                 Arch      Compiler     Host OS   Distribution")
            for index, identifier in enumerate(identifiers):
                print("\t[{:02}] Toolchain: {:>6}  {:^14}  {:^7}  {:^14}"
                      .format(index, identifier.architecture.value, str(identifier.compiler),
                              identifier.hostSystem.value, identifier.installationSource.value))
            try:
                index = int(input("\nInput the toolchain number and press ENTER: "))
                if index not in range(0, len(toolchains)):
                    raise ValueError
                identifier = identifiers[index]
                self.apply_compiler_toolchain(toolchains[identifier], profiles_dbg[identifier], profiles_rel[identifier])
                break
            except ValueError:
                print("Please input a valid compiler toolchain number and try again.")
                continue
            except FileNotFoundError:
                print("Failed to find the Conan profile that matches the selected compiler toolchain.")
                print("Please select another compiler toolchain and try again.")
                continue

    def generate_xcode_configuration_with_profile(self, profile: str, config: str) -> None:
        """
        [Action] Generate the Xcode configuration from the given Conan profile
        """
        path = tempfile.mkdtemp()
        subprocess.run(["conan", "install", ".", "--install-folder", path, "--build", "missing", "--profile", profile]).check_returncode()
        shutil.copy(path + "/" + kXcodeConfigFile, "./" + config)
        shutil.rmtree(path)

    def generate_xcode_configuration(self) -> None:
        """
        [Action] Generate the Xcode configuration from the current Conan profile
        """
        self.generate_xcode_configuration_with_profile(kCurrentConanProfileDebug, kXcodeConfigFileDebug)
        self.generate_xcode_configuration_with_profile(kCurrentConanProfileRelease, kXcodeConfigFileRelease)


# A manager that sets up the compiler toolchain on macOS
class CompilerToolchainManagerMacOS(CompilerToolchainManager):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kMacOS, architecture)

    def install_gcc_10(self) -> None:
        if self.architecture == Architecture.kARM64:
            print("GCC 10 is not available on Apple Silicon-based Mac.")
        else:
            brew_install(["gcc@10"])

    def install_gcc_11(self) -> None:
        brew_install(["gcc@11"])

    def install_gcc_12(self) -> None:
        brew_install(["gcc@12"])

    def install_clang_13(self) -> None:
        brew_install(["llvm@13"])

    def install_clang_14(self) -> None:
        brew_install(["llvm@14"])

    def install_clang_15(self) -> None:
        brew_install(["llvm@15"])


# A manager that sets up the compiler toolchain on Ubuntu
class CompilerToolchainManagerUbuntu(CompilerToolchainManager):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kUbuntu, architecture)

    def install_clang_from_apt_llvm_org(self, version: int) -> None:
        path = tempfile.mkdtemp()
        subprocess.run(["wget", "https://apt.llvm.org/llvm.sh"], cwd=path).check_returncode()
        script = path + "/llvm.sh"
        os.chmod(script, 0o755)
        subprocess.run(["sudo", script, version]).check_returncode()
        apt_install(["libc++-{}-dev".format(version), "libc++abi-{}-dev".format(version)])
        shutil.rmtree(path)


# A manager that sets up the compiler toolchain on Ubuntu 20.04 LTS
class CompilerToolchainManagerUbuntu2004(CompilerToolchainManagerUbuntu):
    def install_gcc_10(self) -> None:
        apt_install(["gcc-10", "g++-10"])

    def install_gcc_11(self) -> None:
        apt_add_repository("ppa:ubuntu-toolchain-r/test")
        apt_install(["gcc-11", "g++-11"])

    def install_gcc_12(self) -> None:
        print("Note that GCC 12 may not be available on Ubuntu 20.04 LTS.")
        apt_add_repository("ppa:ubuntu-toolchain-r/test")
        apt_install(["gcc-12", "g++-12"])

    def install_clang_13(self) -> None:
        self.install_clang_from_apt_llvm_org(13)

    def install_clang_14(self) -> None:
        self.install_clang_from_apt_llvm_org(14)

    def install_clang_15(self) -> None:
        self.install_clang_from_apt_llvm_org(15)


# A manager that sets up the compiler toolchain on Ubuntu 22.04 LTS
class CompilerToolchainManagerUbuntu2204(CompilerToolchainManagerUbuntu):
    def install_gcc_10(self) -> None:
        apt_install(["gcc-10", "g++-10"])

    def install_gcc_11(self) -> None:
        print("GCC 11 is the default compiler toolchain on Ubuntu 22.04 LTS.")
        print("Installation is not required.")

    def install_gcc_12(self) -> None:
        apt_install(["gcc-12", "g++-12"])

    def install_clang_13(self) -> None:
        apt_install(["clang-13", "lldb-13", "lld-13", "libc++-13-dev", "libc++abi-13-dev", "libunwind-13-dev"])

    def install_clang_14(self) -> None:
        apt_install(["clang-14", "lldb-14", "lld-14", "libc++-14-dev", "libc++abi-14-dev", "libunwind-14-dev"])

    def install_clang_15(self) -> None:
        self.install_clang_from_apt_llvm_org(15)


# A manager that sets up the compiler toolchain on Windows
class CompilerToolchainManagerWindows(CompilerToolchainManager):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kWindows, architecture)

    def install_gcc_10(self) -> None:
        print("Compiling this project with GCC 10 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_gcc_11(self) -> None:
        print("Compiling this project with GCC 11 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_gcc_12(self) -> None:
        print("Compiling this project with GCC 12 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_clang_13(self) -> None:
        print("Compiling this project with Clang 13 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_clang_14(self) -> None:
        print("Compiling this project with Clang 14 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_clang_15(self) -> None:
        print("Compiling this project with Clang 15 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")
