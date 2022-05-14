#
# MARK: - Manage Compiler Toolchains
#

import shutil
import tempfile
from BuildSystemDescriptor import *
from Utilities import *

kCurrentToolchainFile = "CurrentToolchain.cmake"
kCurrentConanProfile = "CurrentProfile.conanprofile"
kXcodeConfigFile = "conanbuildinfo.xcconfig"


# An abstract manager that sets up the compiler toolchain on the host system
class CompilerToolchainManager:
    # Filter out toolchains that run on a different host system
    hostSystem: HostSystem
    # Filter out toolchains that have a different architecture
    architecture: Architecture

    def __init__(self, host: HostSystem, architecture: Architecture):
        self.hostSystem = host
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

    def install_all_compilers(self) -> None:
        self.install_gcc_10()
        self.install_gcc_11()
        self.install_gcc_12()
        self.install_clang_13()
        self.install_clang_14()

    def fetch_all_conan_profiles(self, folder: str) -> list[ConanProfile]:
        """
        [Helper] Fetch all conan profiles at the given folder
        :param folder: Path to the folder that stores conan profiles
        :return: A list of parsed conan profiles.
        """
        return [ConanProfile(filename)
                for filename in filter(lambda filename: filename.endswith(".conanprofile"), os.listdir(folder))]

    def fetch_compatible_conan_profiles(self, folder: str) -> list[ConanProfile]:
        """
        [Helper] Fetch all conan profiles compatible with the current host system at the given folder
        :param folder: Path to the folder that stores conan profiles
        :return: A list of parsed conan profiles.
        """
        return list(filter(lambda profile: profile.compatible(self.hostSystem, self.architecture), self.fetch_all_conan_profiles(folder)))

    def fetch_all_compiler_toolchains(self, folder: str) -> list[Toolchain]:
        """
        [Helper] Fetch all CMake compiler toolchains at the given folder
        :param folder: Path to the folder that stores CMake compiler toolchains
        :return: A list of parsed compiler toolchains.
        """
        return [Toolchain(filename)
                for filename in filter(lambda filename: filename.endswith(".cmake"), os.listdir(folder))]

    def fetch_compatible_compiler_toolchains(self, folder: str) -> list[Toolchain]:
        """
        [Helper] Fetch all CMake compiler toolchains compatible with the current host system at the given folder
        :param folder: Path to the folder that stores CMake compiler toolchains
        :return: A list of parsed compiler toolchains.
        """
        return sorted(list(filter(lambda toolchain: toolchain.compatible(self.hostSystem, self.architecture), self.fetch_all_compiler_toolchains(folder))))

    def apply_compiler_toolchain(self, toolchain: Toolchain, profile: ConanProfile) -> None:
        """
        [Action] [Helper] Apply the given combination of the compiler toolchain and the Conan profile
        :param toolchain: The compiler toolchain
        :param profile: The Conan profile
        """
        print("Applying the compiler toolchain:", toolchain)
        print("Applying the Conan profile:", profile)
        if os.path.exists(kCurrentToolchainFile):
            os.remove(kCurrentToolchainFile)
        if os.path.exists(kCurrentConanProfile):
            os.remove(kCurrentConanProfile)
        os.symlink("Toolchains/{}".format(toolchain.filename), kCurrentToolchainFile)
        os.symlink("Profiles/{}".format(profile.filename), kCurrentConanProfile)
        print()
        print("The toolchain and the corresponding Conan profile are both set.")

    def select_compiler_toolchain(self) -> None:
        """
        [Action] Select a compiler toolchain
        """
        toolchains = self.fetch_compatible_compiler_toolchains("Toolchains")
        profiles = self.fetch_compatible_conan_profiles("Profiles")
        while True:
            os.system("clear")
            print("\n>> Available Compiler Toolchains:\n")
            print("\t                 Arch      Compiler     Host OS   Distribution")
            for index, toolchain in enumerate(toolchains):
                print("\t[{:02}] Toolchain: {:>6}  {:^14}  {:^7}  {:^14}"
                      .format(index, toolchain.architecture.value, str(toolchain.compiler),
                              toolchain.hostSystem.value, toolchain.installationSource.value))
            try:
                index = int(input("\nInput the toolchain number and press ENTER: "))
                if index not in range(0, len(toolchains)):
                    raise ValueError
                toolchain = toolchains[index]
                print("Selected Toolchain:", toolchain)
                profile = next((p for p in profiles if toolchain.matches(p)), None)
                if profile is None:
                    raise FileNotFoundError
                self.apply_compiler_toolchain(toolchain, profile)
                break
            except ValueError:
                print("Please input a valid compiler toolchain number and try again.")
                continue
            except FileNotFoundError:
                print("Failed to find the Conan profile that matches the selected compiler toolchain.")
                print("Please select another compiler toolchain and try again.")
                continue

    def generate_xcode_configuration(self) -> None:
        """
        [Action] Generate the Xcode configuration from the current Conan profile
        """
        path = tempfile.mkdtemp()
        subprocess.run(["conan", "install", ".", "--install-folder", path,
                        "--build", "missing", "--profile", kCurrentConanProfile])
        shutil.copy(path + "/" + kXcodeConfigFile, "./")
        shutil.rmtree(path)


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


# A manager that sets up the compiler toolchain on Ubuntu 20.04 LTS
class CompilerToolchainManagerUbuntu2004(CompilerToolchainManager):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kUbuntu, architecture)

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
        path = tempfile.mkdtemp()
        subprocess.run(["wget", "https://apt.llvm.org/llvm.sh"], cwd=path)
        script = path + "/llvm.sh"
        os.chmod(script, 0o755)
        subprocess.run(["sudo", script, "13"])
        apt_install(["libc++-13-dev", "libc++abi-13-dev"])
        shutil.rmtree(path)

    def install_clang_14(self) -> None:
        path = tempfile.mkdtemp()
        subprocess.run(["wget", "https://apt.llvm.org/llvm.sh"], cwd=path)
        script = path + "/llvm.sh"
        os.chmod(script, 0o755)
        subprocess.run(["sudo", script, "14"])
        apt_install(["libc++-14-dev", "libc++abi-14-dev"])
        shutil.rmtree(path)


# A manager that sets up the compiler toolchain on Ubuntu 22.04 LTS
class CompilerToolchainManagerUbuntu2204(CompilerToolchainManager):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kUbuntu, architecture)

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
