#
# MARK: - Compiler Toolchains and Conan Profiles
#

from __future__ import annotations
from enum import Enum
import os


class BuildType(Enum):
    kDebug = "Debug"
    kRelease = "Release"


class Architecture(Enum):
    kx86_64 = "x86-64"
    kARM32 = "ARM32"
    kARM64 = "ARM64"


class CompilerType(Enum):
    kGCC = "GCC"
    kClang = "Clang"
    kAppleClang = "AppleClang"
    kMSVC = "MSVC"


class Compiler:
    compilerType: CompilerType
    version: int

    def __init__(self, description: str):
        """
        Initialize a compiler from its description
        :param description: A string formatted as "<Identifier>-<Version>"
        """
        tokens: list[str] = description.split("-")
        if len(tokens) != 2:
            raise ValueError
        self.compilerType = CompilerType(tokens[0])
        self.version = int(tokens[1])

    def __eq__(self, other: Compiler) -> bool:
        return self.compilerType == other.compilerType and self.version == other.version

    def __lt__(self, other: Compiler) -> bool:
        return self.compilerType.value < other.compilerType.value or self.version < other.version

    def __str__(self) -> str:
        return "{} {}".format(self.compilerType.value, self.version)


class HostSystem(Enum):
    kMacOS = "macOS"
    kUbuntu = "Ubuntu"
    kWindows = "Windows"


class InstallationSource(Enum):
    kHomebrew = "Homebrew"
    kAPT = "APT"
    kXcode = "Xcode"
    kARM = "ARM"
    kVisualStudio = "VisualStudio"


class BuildSystemDescriptor:
    filename: str
    architecture: Architecture
    compiler: Compiler
    hostSystem: HostSystem
    installationSource: InstallationSource

    def __init__(self, filename: str):
        self.filename = filename
        tokens = filename.removesuffix(os.path.splitext(filename)[-1]).split("_")
        if len(tokens) != 4:
            raise ValueError
        self.architecture = Architecture(tokens[0])
        self.compiler = Compiler(tokens[1])
        self.hostSystem = HostSystem(tokens[2])
        self.installationSource = InstallationSource(tokens[3])

    def __str__(self) -> str:
        return "Arch: {}, Compiler: {}, HostOS: {}, From: {}" \
            .format(self.architecture.value, self.compiler,
                    self.hostSystem.value, self.installationSource.value)

    def __eq__(self, other: BuildSystemDescriptor) -> bool:
        return self.filename == other.filename

    def __lt__(self, other: BuildSystemDescriptor) -> bool:
        return self.architecture.value < other.architecture.value or \
               self.compiler < other.compiler or \
               self.hostSystem.value < other.hostSystem.value or \
               self.installationSource.value < other.installationSource.value

    def matches(self, descriptor: BuildSystemDescriptor) -> bool:
        return self.architecture == descriptor.architecture and self.compiler == descriptor.compiler and \
               self.hostSystem == descriptor.hostSystem and self.installationSource == descriptor.installationSource

    def compatible(self, host: HostSystem, architecture: Architecture) -> bool:
        return self.hostSystem == host and self.architecture == architecture

Toolchain = BuildSystemDescriptor

ConanProfile = Toolchain