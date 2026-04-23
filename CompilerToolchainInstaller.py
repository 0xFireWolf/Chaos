#
# MARK: - Install Compiler Toolchains
#

from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from .BuildSystemDescriptor import HostSystem, Architecture
from .Utilities import apt_install, apt_add_repository, brew_install, pkg_install
from .XcodeFinder import XcodeBundle, XcodeFinder


#
# MARK: - Supported Compiler Versions
#

# Every GCC version that Chaos knows how to install on at least one host system
kSupportedGccVersions: tuple[int, ...] = (10, 11, 12, 13, 14, 15)

# Every Clang version that Chaos knows how to install on at least one host system
kSupportedClangVersions: tuple[int, ...] = (13, 14, 15, 16, 17, 18, 19, 20, 21, 22)

# Every AppleClang version that Chaos knows how to install (non-contiguous — AppleClang 17's successor is 21)
kSupportedAppleClangVersions: tuple[int, ...] = (13, 14, 15, 16, 17, 21)


#
# MARK: - Unsupported Toolchain Error
#

class UnsupportedToolchainError(RuntimeError):
    """
    Raised when a compiler toolchain is not supported on the current host system
    or when the requested version is outside the set of supported versions.
    """
    pass


#
# MARK: - Abstract Base Class
#

class CompilerToolchainInstaller(ABC):
    def __init__(self, host_system: HostSystem, architecture: Architecture):
        """
        Initialize the installer for the given host system and CPU architecture
        :param host_system: The host system on which the compiler will be installed
        :param architecture: The CPU architecture of the host system
        """
        self.host_system = host_system
        self.architecture = architecture

    @abstractmethod
    def install_gcc(self, version: int) -> None:
        """
        Install the given major version of GCC
        :param version: The major version of GCC
        :raise UnsupportedToolchainError: if the given version is not supported on the current host system.
        :raise CalledProcessError: if failed to install the compiler.
        """
        raise NotImplementedError

    @abstractmethod
    def install_clang(self, version: int) -> None:
        """
        Install the given major version of Clang
        :param version: The major version of Clang
        :raise UnsupportedToolchainError: if the given version is not supported on the current host system.
        :raise CalledProcessError: if failed to install the compiler.
        """
        raise NotImplementedError

    @abstractmethod
    def install_apple_clang(self, version: int) -> None:
        """
        Activate the given major version of AppleClang
        :param version: The major version of AppleClang
        :raise UnsupportedToolchainError: if the given version is not supported on the current host system.
        :raise CalledProcessError: if failed to activate the compiler.
        :raise RuntimeError: if failed to find a matching Xcode installation on the host system.
        """
        raise NotImplementedError

    def install_all_compilers(self) -> None:
        """
        Install every supported compiler version on the current host system

        Versions that are not supported on the current host system are silently skipped;
        all other errors (e.g., missing Xcode installations, package manager failures) propagate.
        """
        for version in kSupportedGccVersions:
            try:
                self.install_gcc(version)
            except UnsupportedToolchainError as error:
                print(error)
        for version in kSupportedClangVersions:
            try:
                self.install_clang(version)
            except UnsupportedToolchainError as error:
                print(error)


#
# MARK: - macOS
#

class CompilerToolchainInstallerMacOS(CompilerToolchainInstaller):
    # A table that associates each supported AppleClang version with a list of candidate Xcode versions
    #
    # Each candidate is a pair (major, minor) where `minor` may be `None` to match any minor version.
    # The first candidate that corresponds to an installed Xcode bundle on the host system is selected.
    # Candidates are ordered from most to least preferred within each AppleClang version.
    kAppleClangXcodeCandidates: dict[int, list[tuple[int, int | None]]] = {
        # Apple Clang 13.0.0 -> Xcode 13.0, 13.1, 13.2, 13.2.1
        # Apple Clang 13.1.6 -> Xcode 13.3, 13.3.1, 13.4, 13.4.1
        13: [(13, None)],

        # Apple Clang 14.0.0 -> Xcode 14.0, 14.0.1, 14.1.0, 14.2.0
        # Apple Clang 14.0.3 -> Xcode 14.3, 14.3.1
        14: [(14, None)],

        # Apple Clang 15.0.0 -> Xcode 15.0, 15.0.1, 15.1, 15.2, 15.3, 15.4
        15: [(15, None)],

        # Apple Clang 16.0.0 -> Xcode 16.0, 16.1, 16.2
        16: [(16, 2), (16, 1), (16, 0)],

        # Apple Clang 17.0.0 -> Xcode 16.3, 16.4, 26.0, 26.0.1, 26.1, 26.2, 26.3
        17: [(26, 3), (26, 2), (26, 1), (26, 0), (16, 4), (16, 3)],

        # Apple Clang 21.0.0 -> Xcode 26.4, 26.4.1
        21: [(26, 4)],
    }

    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kMacOS, architecture)
        self.xcode_finder = XcodeFinder([Path("/Applications")], r"Xcode.*\.app")

    #
    # MARK: GCC
    #

    def install_gcc(self, version: int) -> None:
        if version not in kSupportedGccVersions:
            raise UnsupportedToolchainError(f"GCC {version} is not a supported version on macOS.")
        if version == 10 and self.architecture == Architecture.kARM64:
            raise UnsupportedToolchainError("GCC 10 is not available on Apple Silicon-based Mac.")
        brew_install([f"gcc@{version}"])

    #
    # MARK: Clang
    #

    def install_clang(self, version: int) -> None:
        if version not in kSupportedClangVersions:
            raise UnsupportedToolchainError(f"Clang {version} is not a supported version on macOS.")
        brew_install([f"llvm@{version}"])

    #
    # MARK: AppleClang
    #

    def find_xcode_in_range(self, major: int, minor: int | None) -> XcodeBundle | None:
        """
        Find the latest Xcode installation whose major (and optionally minor) version matches
        :param major: The major Xcode version to match
        :param minor: The minor Xcode version to match, or `None` to match any minor version
        :return: The matching Xcode bundle with the highest version, or `None` if none is installed.
        """
        matches = [bundle for bundle in self.xcode_finder.find_all()
                   if bundle.version.major == major and (minor is None or bundle.version.minor == minor)]
        return max(matches, key=lambda bundle: bundle.version) if matches else None

    def activate_xcode_from_candidates(self, version: int, candidates: list[tuple[int, int | None]]) -> None:
        """
        Activate the first Xcode installation from the given list of candidates that exists on the host system
        :param version: The AppleClang version being installed (used only for diagnostic messages)
        :param candidates: A list of (major, optional-minor) pairs to try in order
        :raise RuntimeError: if no candidate corresponds to an installed Xcode bundle.
        """
        for major, minor in candidates:
            minor_str = "*" if minor is None else str(minor)
            print(f"Trying to find Xcode {major}.{minor_str}...", flush=True)
            bundle = self.find_xcode_in_range(major, minor)
            if bundle is not None:
                print(f"Found Xcode {bundle.version} at {bundle.path}.", flush=True)
                bundle.activate()
                print(">> The current active Xcode developer directory:", flush=True)
                print(subprocess.check_output(["xcode-select", "-p"], text=True), flush=True)
                print(">> The current active Apple Clang compiler:", flush=True)
                print(subprocess.check_output(["clang", "-v"], text=True), flush=True)
                return
            print(f"No Xcode {major}.{minor_str} installation was found on your local machine.", flush=True)
        raise RuntimeError(f"Failed to find an Xcode installation that ships AppleClang {version}.")

    def install_apple_clang(self, version: int) -> None:
        candidates = self.kAppleClangXcodeCandidates.get(version)
        if candidates is None:
            raise UnsupportedToolchainError(f"AppleClang {version} is not a supported version on macOS.")
        if not candidates:
            raise UnsupportedToolchainError(
                f"AppleClang {version} is recognized but Chaos does not yet know which Xcode version ships it."
            )
        self.activate_xcode_from_candidates(version, candidates)


#
# MARK: - Ubuntu (Base)
#

class CompilerToolchainInstallerUbuntu(CompilerToolchainInstaller, ABC):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kUbuntu, architecture)

    def install_apple_clang(self, version: int) -> None:
        raise UnsupportedToolchainError(f"AppleClang {version} is not available on systems other than macOS.")

    #
    # MARK: Shared APT Helpers
    #

    def install_gcc_from_apt(self, version: int) -> None:
        """
        [Helper] Install the given major version of GCC from the APT repository
        :param version: The major version of GCC
        :raise CalledProcessError: if failed to install the compiler.
        """
        apt_install([f"gcc-{version}", f"g++-{version}"])

    def install_clang_from_apt(self, version: int) -> None:
        """
        [Helper] Install the given major version of Clang from the APT repository
        :param version: The major version of Clang
        :raise CalledProcessError: if failed to install the compiler.
        """
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
        """
        [Helper] Install the given major version of Clang from `apt.llvm.org`
        :param version: The major version of Clang
        :raise CalledProcessError: if failed to install the compiler.
        """
        path = tempfile.mkdtemp()
        try:
            subprocess.run(["wget", "https://apt.llvm.org/llvm.sh"], cwd=path).check_returncode()
            script = path + "/llvm.sh"
            os.chmod(script, 0o755)
            subprocess.run(["sudo", script, str(version)]).check_returncode()
            self.install_clang_from_apt(version)
        finally:
            shutil.rmtree(path, ignore_errors=True)


#
# MARK: - Ubuntu 24.04 LTS
#

class CompilerToolchainInstallerUbuntu2404(CompilerToolchainInstallerUbuntu):
    def install_gcc(self, version: int) -> None:
        if version not in kSupportedGccVersions:
            raise UnsupportedToolchainError(f"GCC {version} is not a supported version on Ubuntu 24.04.")
        if 10 <= version <= 14:
            self.install_gcc_from_apt(version)
        elif version == 15:
            apt_add_repository("ppa:ubuntu-toolchain-r/test")
            self.install_gcc_from_apt(version)
        else:
            raise UnsupportedToolchainError(f"GCC {version} is not available on Ubuntu 24.04.")

    def install_clang(self, version: int) -> None:
        if version not in kSupportedClangVersions:
            raise UnsupportedToolchainError(f"Clang {version} is not a supported version on Ubuntu 24.04.")
        elif 14 <= version <= 19:
            self.install_clang_from_apt(version)
        elif 20 <= version <= 22:
            self.install_clang_from_apt_llvm_org(version)
        else:
            raise UnsupportedToolchainError(f"Clang {version} is not available on Ubuntu 24.04.")


#
# MARK: - Ubuntu 26.04 LTS
#

class CompilerToolchainInstallerUbuntu2604(CompilerToolchainInstallerUbuntu):
    # https://documentation.ubuntu.com/ubuntu-for-developers/reference/availability/gcc/#gcc-toolchain-availability
    def install_gcc(self, version: int) -> None:
        if version not in kSupportedGccVersions:
            raise UnsupportedToolchainError(f"GCC {version} is not a supported version on Ubuntu 26.04.")
        if version == 10:
            brew_install(["gcc@10"])
        elif 11 <= version <= 15:
            self.install_gcc_from_apt(version)
        else:
            raise UnsupportedToolchainError(f"GCC {version} is not available on Ubuntu 26.04.")

    # https://documentation.ubuntu.com/ubuntu-for-developers/reference/availability/llvm/#llvm-toolchain-availability
    def install_clang(self, version: int) -> None:
        if version not in kSupportedClangVersions:
            raise UnsupportedToolchainError(f"Clang {version} is not a supported version on Ubuntu 26.04.")
        elif 14 <= version <= 16:
            brew_install([f"llvm@{version}"])
        elif 17 <= version <= 21:
            self.install_clang_from_apt(version)
        elif 22 == version:
            self.install_clang_from_apt_llvm_org(version)
        else:
            raise UnsupportedToolchainError(f"GCC {version} is not available on Ubuntu 26.04.")


#
# MARK: - FreeBSD
#

class CompilerToolchainInstallerFreeBSD(CompilerToolchainInstaller):
    def __init__(self, architecture: Architecture):
        super().__init__(HostSystem.kFreeBSD, architecture)

    def install_gcc(self, version: int) -> None:
        if version not in kSupportedGccVersions:
            raise UnsupportedToolchainError(f"GCC {version} is not a supported version on FreeBSD.")
        pkg_install([f"gcc{version}"])

    def install_clang(self, version: int) -> None:
        if version not in kSupportedClangVersions:
            raise UnsupportedToolchainError(f"Clang {version} is not a supported version on FreeBSD.")
        pkg_install([f"llvm{version}"])

    def install_apple_clang(self, version: int) -> None:
        raise UnsupportedToolchainError(f"AppleClang {version} is not available on systems other than macOS.")


#
# MARK: - Unsupported Host System (Used on Windows)
#

class CompilerToolchainInstallerUnsupported(CompilerToolchainInstaller):
    """
    A drop-in installer for host systems on which Chaos does not manage compiler toolchains

    Used on Windows, where developers are expected to install MSVC via the Visual Studio installer.
    All install methods unconditionally raise `UnsupportedToolchainError`.
    """

    def install_gcc(self, version: int) -> None:
        raise UnsupportedToolchainError(
            f"Installing GCC {version} via Chaos is not supported on {self.host_system.value}. "
            f"Please use Microsoft Visual C++ on Windows."
        )

    def install_clang(self, version: int) -> None:
        raise UnsupportedToolchainError(
            f"Installing Clang {version} via Chaos is not supported on {self.host_system.value}. "
            f"Please use Microsoft Visual C++ on Windows."
        )

    def install_apple_clang(self, version: int) -> None:
        raise UnsupportedToolchainError(
            f"AppleClang {version} is not available on systems other than macOS."
        )
