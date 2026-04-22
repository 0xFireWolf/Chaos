#
# MARK: - A Semver-style Version Number
#

from __future__ import annotations
from functools import total_ordering


@total_ordering
class Version:
    def __init__(self, major: int, minor: int = 0, patch: int = 0):
        """
        Initialize a version number from its components
        :param major: The major version component
        :param minor: The minor version component (Default: 0)
        :param patch: The patch version component (Default: 0)
        """
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def parse(cls, string: str) -> Version:
        """
        Parse a version number from its string representation
        :param string: A string formatted as "X", "X.Y", or "X.Y.Z"
        :return: The parsed version number.
        :raise ValueError: if the given string is not a valid version number.
        """
        tokens = string.split(".")
        if len(tokens) < 1 or len(tokens) > 3:
            raise ValueError(f"'{string}' is not a valid version number.")
        try:
            components = [int(token) for token in tokens]
        except ValueError:
            raise ValueError(f"'{string}' is not a valid version number.")
        return cls(*components)

    def __eq__(self, other: Version) -> bool:
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: Version) -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"Version({self.major}, {self.minor}, {self.patch})"
