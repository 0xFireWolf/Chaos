#
# MARK: - Python Helpers
#

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
