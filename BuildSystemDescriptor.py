#
# MARK: - Compiler Toolchains and Conan Profiles
#

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .Sidekicks import OrderedStrEnum


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


@dataclass(frozen=True, order=True)
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
            compiler_type = CompilerType(tokens[0])
        except ValueError:
            raise ValueError(f"'{tokens[0]}' is not a valid compiler type.")
        try:
            compiler_version = int(tokens[1])
        except ValueError:
            raise ValueError(f"'{tokens[1]}' is not a valid compiler version.")
        return cls(compiler_type, compiler_version)

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


@dataclass(frozen=True, order=True)
class BuildSystemIdentifier:
    """
    A 5-tuple that identifies a specific toolchain/profile
    """
    architecture: Architecture
    compiler: Compiler
    standard_library: StandardLibrary
    host_system: HostSystem
    installation_source: InstallationSource

    @classmethod
    def from_strings(cls,
                     architecture: str,
                     compiler: str,
                     standard_library: str,
                     host_system: str,
                     installation_source: str) -> BuildSystemIdentifier:
        return cls(Architecture(architecture),
                   Compiler.parse(compiler),
                   StandardLibrary(standard_library),
                   HostSystem(host_system),
                   InstallationSource(installation_source))

    @classmethod
    def from_tokens(cls, tokens: list[str]) -> BuildSystemIdentifier:
        match tokens:
            case [architecture, compiler, host_system, installation_source]:
                return cls.from_strings(architecture, compiler, "Default", host_system, installation_source)
            case [architecture, compiler, standard_library, host_system, installation_source]:
                return cls.from_strings(architecture, compiler, standard_library, host_system, installation_source)
            case _:
                raise ValueError(f"Expected 4 or 5 identifier tokens, got {len(tokens)}: {tokens}.")

    def compatible(self, host_system: HostSystem, architecture: Architecture) -> bool:
        return self.host_system == host_system and self.architecture == architecture


@dataclass(frozen=True)
class CMakeToolchain:
    filename: str
    identifier: BuildSystemIdentifier

    @classmethod
    def parse(cls, path: Path) -> CMakeToolchain:
        filename = path.name
        try:
            identifier = BuildSystemIdentifier.from_tokens(path.stem.split("_"))
        except ValueError as error:
            raise ValueError(f"'{filename}' is not a valid CMake toolchain filename: {error}.") from error
        return cls(filename, identifier)

    def __str__(self) -> str:
        return self.filename


@dataclass(frozen=True)
class ConanProfile:
    filename: str
    identifier: BuildSystemIdentifier
    build_type: BuildType

    @classmethod
    def parse(cls, path: Path) -> ConanProfile:
        filename = path.stem
        tokens = filename.split("_")
        if len(tokens) not in (5, 6):
            raise ValueError(f"'{filename}' is not a valid Conan profile name.")
        *identifier_tokens, build_type_str = tokens
        try:
            identifier = BuildSystemIdentifier.from_tokens(identifier_tokens)
        except ValueError as error:
            raise ValueError(f"'{filename}' is not a valid Conan profile name: {error}.") from error
        try:
            build_type = BuildType(build_type_str)
        except ValueError as error:
            raise ValueError(f"'{filename}' is not a valid Conan profile name: {error}.") from error
        return cls(filename, identifier, build_type)

    def __str__(self) -> str:
        return self.filename


@dataclass(frozen=True)
class ConanProfilePair:
    debug: ConanProfile
    release: ConanProfile
