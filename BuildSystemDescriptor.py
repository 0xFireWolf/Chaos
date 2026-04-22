#
# MARK: - Compiler Toolchains and Conan Profiles
#

from dataclasses import dataclass
from .Sidekicks import OrderedStrEnum
import os
from functools import total_ordering


class BuildType(OrderedStrEnum):
    kDebug = "Debug"
    kRelease = "Release"


class Architecture(OrderedStrEnum):
    kx86_64 = "x86-64"
    kARM32 = "ARM32"
    kARM64 = "ARM64"


class CompilerType(OrderedStrEnum):
    kGCC = "GCC"
    kClang = "Clang"
    kAppleClang = "AppleClang"
    kMSVC = "MSVC"


@dataclass(frozen=True, order=True, unsafe_hash=True)
class Compiler:
    type: CompilerType
    version: int

    @classmethod
    def parse(cls, description: str) -> Compiler:
        """
        Initialize a compiler from its description
        :param description: A string formatted as "<Identifier>-<Version>"
        """
        tokens = description.split("-")
        if len(tokens) != 2:
            raise ValueError(f"'{description}' is not a valid compiler description.")
        try:
            type = CompilerType(tokens[0])
        except ValueError:
            raise ValueError(f"'{tokens[0]}' is not a valid compiler type.")
        try:
            version = int(tokens[1])
        except ValueError:
            raise ValueError(f"'{tokens[1]}' is not a valid compiler version.")
        return cls(type, version)

    def __str__(self) -> str:
        return f"{self.type} {self.version}"


class StandardLibrary(OrderedStrEnum):
    kGNU = "libstdc++"
    kClang = "libc++"
    kDefault = "Default"


class HostSystem(OrderedStrEnum):
    kMacOS = "macOS"
    kUbuntu = "Ubuntu"
    kWindows = "Windows"
    kFreeBSD = "FreeBSD"


class InstallationSource(OrderedStrEnum):
    kHomebrew = "Homebrew"
    kAPT = "APT"
    kXcode = "Xcode"
    kARM = "ARM"
    kVisualStudio = "VisualStudio"
    kPKG = "PKG"


@dataclass(frozen=True, order=True, unsafe_hash=True)
class BuildSystemIdentifier:
    architecture: Architecture
    compiler: Compiler
    standard_library: StandardLibrary
    host_system: HostSystem
    installation_source: InstallationSource

    @classmethod
    def from_strings(cls,
                     architecture_string: str,
                     compiler_string: str,
                     standard_library_string: str,
                     host_system_string: str,
                     installation_source_string: str) -> BuildSystemIdentifier:
        """
         A 4-tuple that identifies a specific toolchain/profile
        """
        try:
            architecture = Architecture(architecture_string)
        except ValueError:
            raise ValueError(f"'{architecture_string}' is not a valid architecture.")
        compiler = Compiler.parse(compiler_string)
        try:
            standard_library = StandardLibrary(standard_library_string)
        except ValueError:
            raise ValueError(f"'{standard_library_string}' is not a valid standard library.")
        try:
            host_system = HostSystem(host_system_string)
        except ValueError:
            raise ValueError(f"'{host_system_string}' is not a valid host system.")
        try:
            installation_source = InstallationSource(installation_source_string)
        except ValueError:
            raise ValueError(f"'{installation_source_string}' is not a valid installation source.")
        return cls(architecture, compiler, standard_library, host_system, installation_source)

    def compatible(self, host_system: HostSystem, architecture: Architecture) -> bool:
        return self.host_system == host_system and self.architecture == architecture


@dataclass(frozen=True)
class CMakeToolchain:
    filename: str
    identifier: BuildSystemIdentifier

    @classmethod
    def parse(cls, path: Path) -> CMakeToolchain:
        filename = path.stem
        tokens = filename.split("_")
        if len(tokens) == 4:
            identifier = BuildSystemIdentifier.from_strings(tokens[0], tokens[1], "Default", tokens[2], tokens[3])
        elif len(tokens) == 5:
            identifier = BuildSystemIdentifier.from_strings(tokens[0], tokens[1], tokens[2], tokens[3], tokens[4])
        else:
            raise ValueError(f"'{filename}' is not a valid toolchain name.")
        return cls(filename, identifier)

    def __str__(self) -> str:
        return self.filename


class ConanProfile:
    def __init__(self, filename: str):
        tokens = filename.removesuffix(os.path.splitext(filename)[-1]).split("_")
        if len(tokens) == 5:
            self.identifier = BuildSystemIdentifier(tokens[0], tokens[1], "Default", tokens[2], tokens[3])
            self.buildType = BuildType(tokens[4])
        elif len(tokens) == 6:
            self.identifier = BuildSystemIdentifier(tokens[0], tokens[1], tokens[2], tokens[3], tokens[4])
            self.buildType = BuildType(tokens[5])
        else:
            raise ValueError
        self.filename = filename

    def __str__(self) -> str:
        return self.filename


class ConanProfilePair:
    def __init__(self, debug: ConanProfile = None, release: ConanProfile = None):
        self.debug = debug
        self.release = release
