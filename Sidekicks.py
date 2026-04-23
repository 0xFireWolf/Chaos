#
# MARK: - Python Helpers
#

from __future__ import annotations
from enum import StrEnum

class OrderedStrEnum(StrEnum):
    def __lt__(self, other: OrderedStrEnum):
        return self.value < other.value

    def __le__(self, other: OrderedStrEnum):
        return self.value <= other.value

    def __gt__(self, other: OrderedStrEnum):
        return self.value > other.value

    def __ge__(self, other: OrderedStrEnum):
        return self.value >= other.value
