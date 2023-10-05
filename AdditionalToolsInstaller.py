#
# MARK: - Define the interface of installing additional tools
#

from abc import ABC, abstractmethod


class AdditionalToolInstaller(ABC):
    @abstractmethod
    def macos(self) -> None:
        print("This project does not require any additional development tools on macOS.")

    @abstractmethod
    def ubuntu(self) -> None:
        print("This project does not require any additional development tools on Ubuntu.")

    @abstractmethod
    def windows(self) -> None:
        print("This project does not require any additional development tools on Windows.")
