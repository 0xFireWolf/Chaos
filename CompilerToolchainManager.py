#
# MARK: - Manage Compiler Toolchains
#

import tempfile
from abc import ABC, abstractmethod
from functools import cached_property
from .BuildSystemDescriptor import *
from .Utilities import *
from .XcodeFinder import *

kCurrentToolchainFile = "CurrentToolchain.cmake"
kCurrentConanBuildProfileDebug = "CurrentBuildProfileDebug.conanprofile"
kCurrentConanBuildProfileRelease = "CurrentBuildProfileRelease.conanprofile"
kCurrentConanHostProfileDebug = "CurrentHostProfileDebug.conanprofile"
kCurrentConanHostProfileRelease = "CurrentHostProfileRelease.conanprofile"


# An abstract manager that sets up the compiler toolchain on the host system
class CompilerToolchainManager(ABC):
    def __init__(self, host: HostSystem, architecture: Architecture):
        # Filter out toolchains that run on a different host system
        self.host_system = host
        # Filter out toolchains that have a different architecture
        self.architecture = architecture

    @property
    def cmake_toolchains_folder_name(self) -> str:
        # The name of the folder in which CMake toolchains are stores
        return "Toolchains"

    @cached_property
    def conan_profiles_folder_name(self) -> str:
        # The name of the folder in which Conan profiles are stored
        return "Profiles2" if is_conan_v2_installed() else "Profiles"

    @abstractmethod
    def install_gcc_10(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_gcc_11(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_gcc_12(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_gcc_13(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_gcc_14(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_clang_13(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_clang_14(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_clang_15(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_clang_16(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_clang_17(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_clang_18(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_clang_19(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_apple_clang_13(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_apple_clang_14(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_apple_clang_15(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_apple_clang_16(self) -> None:
        raise NotImplementedError

    def install_all_compilers(self) -> None:
        self.install_gcc_10()
        self.install_gcc_11()
        self.install_gcc_12()
        self.install_gcc_13()
        self.install_gcc_14()
        self.install_clang_13()
        self.install_clang_14()
        self.install_clang_15()
        self.install_clang_16()
        self.install_clang_17()
        self.install_clang_18()
        self.install_clang_19()

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
        return list(filter(lambda profile: profile.identifier.compatible(self.host_system, self.architecture),
                           self.fetch_all_conan_profiles(folder)))

    def fetch_compatible_conan_profiles_as_map(self, folder: str) -> (dict[BuildSystemIdentifier, ConanProfile],
                                                                      dict[BuildSystemIdentifier, ConanProfile]):
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
        return list(filter(lambda toolchain: toolchain.identifier.compatible(self.host_system, self.architecture),
                           self.fetch_all_compiler_toolchains(folder)))

    def fetch_compatible_compiler_toolchains_as_map(self, folder: str) -> dict[BuildSystemIdentifier, Toolchain]:
        """
        [Helper] Fetch all CMake compiler toolchains compatible with the current host system at the given folder and build the toolchain map
        :param folder: Path to the folder that stores CMake compiler toolchains
        :return: A map keyed by the toolchain identifier.
        :raise: `ValueError` if failed to parse one of the toolchains in the given folder.
        """
        return {toolchain.identifier: toolchain for toolchain in self.fetch_compatible_compiler_toolchains(folder)}

    def apply_compiler_toolchain(self, toolchain: Toolchain,
                                 build_profile_debug: ConanProfile,
                                 build_profile_release: ConanProfile,
                                 host_profile_debug: ConanProfile = None,
                                 host_profile_release: ConanProfile = None) -> None:
        """
        [Action] [Helper] Apply the given combination of the compiler toolchain and the Conan profile
        :param build_profile_debug: The Conan profile that specifies the build environment (debug build)
        :param build_profile_release: The Conan profile that specifies the build environment (release build)
        :param host_profile_debug: The Conan profile that specifies the host environment (debug build)
        :param host_profile_release: The Conan profile that specifies the host environment (release build)
        :param toolchain: The compiler toolchain
        """
        if host_profile_debug is None:
            host_profile_debug = build_profile_debug
        if host_profile_release is None:
            host_profile_release = build_profile_release
        print("Applying the compiler toolchain:", toolchain.filename)
        print("Applying the Conan build profile (Debug):", build_profile_debug.filename)
        print("Applying the Conan build profile (Release):", build_profile_release.filename)
        print("Applying the Conan host profile (Debug):", host_profile_debug.filename)
        print("Applying the Conan host profile (Release):", host_profile_release.filename)
        remove_file_if_exist(Path(kCurrentToolchainFile))
        remove_file_if_exist(Path(kCurrentConanBuildProfileDebug))
        remove_file_if_exist(Path(kCurrentConanBuildProfileRelease))
        remove_file_if_exist(Path(kCurrentConanHostProfileDebug))
        remove_file_if_exist(Path(kCurrentConanHostProfileRelease))
        os.symlink(Path(self.cmake_toolchains_folder_name) / toolchain.filename, Path(kCurrentToolchainFile))
        os.symlink(Path(self.conan_profiles_folder_name) / build_profile_debug.filename, Path(kCurrentConanBuildProfileDebug))
        os.symlink(Path(self.conan_profiles_folder_name) / build_profile_release.filename, Path(kCurrentConanBuildProfileRelease))
        os.symlink(Path(self.conan_profiles_folder_name) / host_profile_debug.filename, Path(kCurrentConanHostProfileDebug))
        os.symlink(Path(self.conan_profiles_folder_name) / host_profile_release.filename, Path(kCurrentConanHostProfileRelease))
        print()
        print("The toolchain and the corresponding Conan profiles are both set.")

    def select_compiler_toolchain(self) -> None:
        """
        [Action] Select a compiler toolchain
        """
        toolchains = self.fetch_compatible_compiler_toolchains_as_map(self.cmake_toolchains_folder_name)
        profiles_dbg, profiles_rel = self.fetch_compatible_conan_profiles_as_map(self.conan_profiles_folder_name)
        assert len(toolchains.keys()) == len(profiles_dbg.keys())
        assert len(toolchains.keys()) == len(profiles_rel.keys())
        identifiers = sorted(list(toolchains.keys()))
        while True:
            print("\n>> Available Compiler Toolchains:\n")
            print("\t                 Arch      Compiler       Stdlib   Host OS   Distribution")
            for index, identifier in enumerate(identifiers):
                print("\t[{:02}] Toolchain: {:>6}  {:^14}  {:^9}  {:^7}  {:^14}"
                      .format(index,
                              identifier.architecture.value,
                              str(identifier.compiler),
                              identifier.standard_library.value,
                              identifier.host_system.value,
                              identifier.installation_source.value))
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

    def install_gcc_13(self) -> None:
        brew_install(["gcc@13"])

    def install_gcc_14(self) -> None:
        brew_install(["gcc@14"])

    def install_clang_13(self) -> None:
        brew_install(["llvm@13"])

    def install_clang_14(self) -> None:
        brew_install(["llvm@14"])

    def install_clang_15(self) -> None:
        brew_install(["llvm@15"])

    def install_clang_16(self) -> None:
        brew_install(["llvm@16"])

    def install_clang_17(self) -> None:
        brew_install(["llvm@17"])

    def install_clang_18(self) -> None:
        brew_install(["llvm@18"])

    def install_clang_19(self) -> None:
        brew_install(["llvm@19"])

    def select_xcode_installation(self, major: int, minor: int = None, patch: int = None) -> None:
        bundle = XcodeFinder([Path("/Applications")], "Xcode.*\\.app").find(major, minor, patch)
        if bundle is None:
            raise RuntimeError("Xcode {} is not installed on your local machine.".format(major))
        bundle.activate()
        print(">> The current active Xcode installation:")
        print(bundle)
        print(">> The current active Xcode developer directory:")
        print(subprocess.check_output(["xcode-select", "-p"], text=True))
        print(">> The current active Apple Clang compiler:")
        print(subprocess.check_output(["clang", "-v"], text=True))

    def install_apple_clang_13(self) -> None:
        self.select_xcode_installation(13)

    def install_apple_clang_14(self) -> None:
        self.select_xcode_installation(14)

    def install_apple_clang_15(self) -> None:
        self.select_xcode_installation(15)

    def install_apple_clang_16(self) -> None:
        self.select_xcode_installation(16)


# A manager that sets up the compiler toolchain on Ubuntu
class CompilerToolchainManagerUbuntu(CompilerToolchainManager, ABC):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kUbuntu, architecture)

    def install_apple_clang_13(self) -> None:
        print("AppleClang 13 is not available on systems other than macOS.")

    def install_apple_clang_14(self) -> None:
        print("AppleClang 14 is not available on systems other than macOS.")

    def install_apple_clang_15(self) -> None:
        print("AppleClang 15 is not available on systems other than macOS.")

    def install_apple_clang_16(self) -> None:
        print("AppleClang 16 is not available on systems other than macOS.")

    def install_gcc_from_apt(self, version: int) -> None:
        apt_install([f"gcc-{version}", f"g++-{version}"])

    def install_clang_from_apt(self, version: int) -> None:
        apt_install([f"clang-{version}",
                     f"clang-tools-{version}",
                     f"clang-{version}-doc",
                     f"libclang-common-{version}-dev",
                     f"libclang-{version}-dev",
                     f"libclang1-{version}",
                     f"clang-format-{version}",
                     f"python3-clang-{version}",
                     f"clangd-{version}",
                     f"clang-tidy-{version}",
                     f"libc++-{version}-dev",
                     f"libc++abi-{version}-dev",
                     f"libunwind-{version}-dev"])

    def install_clang_from_apt_llvm_org(self, version: int) -> None:
        path = tempfile.mkdtemp()
        subprocess.run(["wget", "https://apt.llvm.org/llvm.sh"], cwd=path).check_returncode()
        script = path + "/llvm.sh"
        os.chmod(script, 0o755)
        subprocess.run(["sudo", script, str(version)]).check_returncode()
        self.install_clang_from_apt(version)
        shutil.rmtree(path)


# A manager that sets up the compiler toolchain on Ubuntu 20.04 LTS
class CompilerToolchainManagerUbuntu2004(CompilerToolchainManagerUbuntu):
    def install_gcc_10(self) -> None:
        self.install_gcc_from_apt(10)

    def install_gcc_11(self) -> None:
        apt_add_repository("ppa:ubuntu-toolchain-r/test")
        self.install_gcc_from_apt(11)

    def install_gcc_12(self) -> None:
        brew_install(["gcc@12"])

    def install_gcc_13(self) -> None:
        brew_install(["gcc@13"])

    def install_gcc_14(self) -> None:
        brew_install(["gcc@14"])

    def install_clang_13(self) -> None:
        self.install_clang_from_apt_llvm_org(13)

    def install_clang_14(self) -> None:
        self.install_clang_from_apt_llvm_org(14)

    def install_clang_15(self) -> None:
        self.install_clang_from_apt_llvm_org(15)

    def install_clang_16(self) -> None:
        self.install_clang_from_apt_llvm_org(16)

    def install_clang_17(self) -> None:
        self.install_clang_from_apt_llvm_org(17)

    def install_clang_18(self) -> None:
        self.install_clang_from_apt_llvm_org(18)

    def install_clang_19(self) -> None:
        self.install_clang_from_apt_llvm_org(19)


# A manager that sets up the compiler toolchain on Ubuntu 22.04 LTS
class CompilerToolchainManagerUbuntu2204(CompilerToolchainManagerUbuntu):
    def install_gcc_10(self) -> None:
        self.install_gcc_from_apt(10)

    def install_gcc_11(self) -> None:
        self.install_gcc_from_apt(11)

    def install_gcc_12(self) -> None:
        self.install_gcc_from_apt(12)

    def install_gcc_13(self) -> None:
        apt_add_repository("ppa:ubuntu-toolchain-r/test")
        self.install_gcc_from_apt(13)

    def install_gcc_14(self) -> None:
        apt_add_repository("ppa:ubuntu-toolchain-r/test")
        self.install_gcc_from_apt(14)

    def install_clang_13(self) -> None:
        self.install_clang_from_apt(13)

    def install_clang_14(self) -> None:
        self.install_clang_from_apt(14)

    def install_clang_15(self) -> None:
        self.install_clang_from_apt_llvm_org(15)

    def install_clang_16(self) -> None:
        self.install_clang_from_apt_llvm_org(16)

    def install_clang_17(self) -> None:
        self.install_clang_from_apt_llvm_org(17)

    def install_clang_18(self) -> None:
        self.install_clang_from_apt_llvm_org(18)

    def install_clang_19(self) -> None:
        self.install_clang_from_apt_llvm_org(19)


# A manager that sets up the compiler toolchain on Ubuntu 24.04 LTS
class CompilerToolchainManagerUbuntu2404(CompilerToolchainManagerUbuntu):
    def install_gcc_10(self) -> None:
        self.install_gcc_from_apt(10)

    def install_gcc_11(self) -> None:
        self.install_gcc_from_apt(11)

    def install_gcc_12(self) -> None:
        self.install_gcc_from_apt(12)

    def install_gcc_13(self) -> None:
        self.install_gcc_from_apt(13)

    def install_gcc_14(self) -> None:
        self.install_gcc_from_apt(14)

    def install_clang_13(self) -> None:
        self.install_clang_from_apt_llvm_org(13)

    def install_clang_14(self) -> None:
        self.install_clang_from_apt(14)

    def install_clang_15(self) -> None:
        self.install_clang_from_apt(15)

    def install_clang_16(self) -> None:
        self.install_clang_from_apt(16)

    def install_clang_17(self) -> None:
        self.install_clang_from_apt(17)

    def install_clang_18(self) -> None:
        self.install_clang_from_apt(18)

    def install_clang_19(self) -> None:
        self.install_clang_from_apt_llvm_org(19)


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

    def install_gcc_13(self) -> None:
        print("Compiling this project with GCC 13 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_gcc_14(self) -> None:
        print("Compiling this project with GCC 14 on Windows is not supported.")
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

    def install_clang_16(self) -> None:
        print("Compiling this project with Clang 16 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_clang_17(self) -> None:
        print("Compiling this project with Clang 17 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_clang_18(self) -> None:
        print("Compiling this project with Clang 18 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_clang_19(self) -> None:
        print("Compiling this project with Clang 19 on Windows is not supported.")
        print("Please use Microsoft Visual C++ instead.")

    def install_apple_clang_13(self) -> None:
        print("AppleClang 13 is not available on systems other than macOS.")

    def install_apple_clang_14(self) -> None:
        print("AppleClang 14 is not available on systems other than macOS.")

    def install_apple_clang_15(self) -> None:
        print("AppleClang 15 is not available on systems other than macOS.")

    def install_apple_clang_16(self) -> None:
        print("AppleClang 16 is not available on systems other than macOS.")


# A manager that sets up the compiler toolchain on FreeBSD
class CompilerToolchainManagerFreeBSD(CompilerToolchainManager):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kFreeBSD, architecture)

    def install_gcc_10(self) -> None:
        pkg_install(["gcc10"])

    def install_gcc_11(self) -> None:
        pkg_install(["gcc11"])

    def install_gcc_12(self) -> None:
        pkg_install(["gcc12"])

    def install_gcc_13(self) -> None:
        pkg_install(["gcc13"])

    def install_gcc_14(self) -> None:
        pkg_install(["gcc14"])

    def install_clang_13(self) -> None:
        pkg_install(["llvm13"])

    def install_clang_14(self) -> None:
        pkg_install(["llvm14"])

    def install_clang_15(self) -> None:
        pkg_install(["llvm15"])

    def install_clang_16(self) -> None:
        pkg_install(["llvm16"])

    def install_clang_17(self) -> None:
        pkg_install(["llvm17"])

    def install_clang_18(self) -> None:
        pkg_install(["llvm18"])

    def install_clang_19(self) -> None:
        pkg_install(["llvm19"])

    def install_apple_clang_13(self) -> None:
        print("AppleClang 13 is not available on systems other than macOS.")

    def install_apple_clang_14(self) -> None:
        print("AppleClang 14 is not available on systems other than macOS.")

    def install_apple_clang_15(self) -> None:
        print("AppleClang 15 is not available on systems other than macOS.")

    def install_apple_clang_16(self) -> None:
        print("AppleClang 16 is not available on systems other than macOS.")
