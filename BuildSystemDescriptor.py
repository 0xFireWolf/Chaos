#
# MARK: - Compiler Toolchains and Conan Profiles
#

from __future__ import annotations
from enum import Enum
import os
from functools import total_ordering


class BuildType(Enum):
    kDebug = "Debug"
    kRelease = "Release"


@total_ordering
class Architecture(Enum):
    kx86_64 = "x86-64"
    kARM32 = "ARM32"
    kARM64 = "ARM64"

    def __eq__(self, other: Architecture) -> bool:
        return self.value == other.value

    def __lt__(self, other: Architecture) -> bool:
        return self.value < other.value

    def __hash__(self):
        return hash(self.value)


@total_ordering
class CompilerType(Enum):
    kGCC = "GCC"
    kClang = "Clang"
    kAppleClang = "AppleClang"
    kMSVC = "MSVC"

    def __eq__(self, other: CompilerType) -> bool:
        return self.value == other.value

    def __lt__(self, other: CompilerType) -> bool:
        return self.value < other.value

    def __hash__(self):
        return hash(self.value)


@total_ordering
class Compiler:
    def __init__(self, description: str):
        """
        Initialize a compiler from its description
        :param description: A string formatted as "<Identifier>-<Version>"
        """
        tokens: list[str] = description.split("-")
        if len(tokens) != 2:
            raise ValueError
        self.type = CompilerType(tokens[0])
        self.version = int(tokens[1])

    def __eq__(self, other: Compiler) -> bool:
        return self.type == other.type and self.version == other.version

    def __lt__(self, other: Compiler) -> bool:
        return (self.type.value, self.version) < (other.type.value, other.version)

    def __str__(self) -> str:
        return "{} {}".format(self.type.value, self.version)

    def __hash__(self):
        return hash((self.type, self.version))


@total_ordering
class StandardLibrary(Enum):
    kGNU = "libstdc++"
    kClang = "libc++"
    kDefault = "Default"

    def __eq__(self, other: StandardLibrary) -> bool:
        return self.value == other.value

    def __lt__(self, other: StandardLibrary) -> bool:
        return self.value < other.value

    def __hash__(self):
        return hash(self.value)


@total_ordering
class HostSystem(Enum):
    kMacOS = "macOS"
    kUbuntu = "Ubuntu"
    kWindows = "Windows"

    def __eq__(self, other: HostSystem) -> bool:
        return self.value == other.value

    def __lt__(self, other: HostSystem) -> bool:
        return self.value < other.value

    def __hash__(self):
        return hash(self.value)


@total_ordering
class InstallationSource(Enum):
    kHomebrew = "Homebrew"
    kAPT = "APT"
    kXcode = "Xcode"
    kARM = "ARM"
    kVisualStudio = "VisualStudio"

    def __eq__(self, other: InstallationSource) -> bool:
        return self.value == other.value

    def __lt__(self, other: InstallationSource) -> bool:
        return self.value < other.value

    def __hash__(self):
        return hash(self.value)


@total_ordering
class BuildSystemIdentifier:
    def __init__(self, architecture: str, compiler: str, standard_library: str,
                 host_system: str, installation_source: str):
        """
         A 4-tuple that identifies a specific toolchain/profile
        """
        self.architecture = Architecture(architecture)
        self.compiler = Compiler(compiler)
        self.standard_library = StandardLibrary(standard_library)
        self.host_system = HostSystem(host_system)
        self.installation_source = InstallationSource(installation_source)

    def __str__(self) -> str:
        return "Arch: {}, Compiler: {}, Stdlib: {}, HostOS: {}, From: {}" \
            .format(self.architecture.value, self.compiler, self.standard_library.value,
                    self.host_system.value, self.installation_source.value)

    def __lt__(self, other: BuildSystemIdentifier) -> bool:
        return self.compiler < other.compiler

    def __eq__(self, other: BuildSystemIdentifier) -> bool:
        return (self.architecture == other.architecture and
                self.compiler == other.compiler and
                self.standard_library == other.standard_library and
                self.host_system == other.host_system and
                self.installation_source == other.installation_source)

    def __hash__(self):
        return hash((self.architecture,
                     self.compiler,
                     self.standard_library,
                     self.host_system,
                     self.installation_source))

    def compatible(self, host_system: HostSystem, architecture: Architecture) -> bool:
        return self.host_system == host_system and self.architecture == architecture


class Toolchain:
    def __init__(self, filename: str):
        tokens = filename.removesuffix(os.path.splitext(filename)[-1]).split("_")
        if len(tokens) == 4:
            self.identifier = BuildSystemIdentifier(tokens[0], tokens[1], "Default", tokens[2], tokens[3])
        elif len(tokens) == 5:
            self.identifier = BuildSystemIdentifier(tokens[0], tokens[1], tokens[2], tokens[3], tokens[4])
        else:
            raise ValueError
        self.filename = filename

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
