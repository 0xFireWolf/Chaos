#
# MARK: - Define the interface of installing additional tools
#

from abc import ABC, abstractmethod


class AdditionalToolInstaller(ABC):
    @abstractmethod
    def macos(self) -> None:
        pass

    @abstractmethod
    def ubuntu(self) -> None:
        pass

    @abstractmethod
    def windows(self) -> None:
        pass

    @abstractmethod
    def freebsd(self) -> None:
        pass


class DefaultAdditionalToolInstaller(AdditionalToolInstaller):
    def macos(self) -> None:
        print("This project does not require any additional development tools on macOS.")

    def ubuntu(self) -> None:
        print("This project does not require any additional development tools on Ubuntu.")

    def windows(self) -> None:
        print("This project does not require any additional development tools on Windows.")

    def freebsd(self) -> None:
        print("This project does not require any additional development tools on FreeBSD.")
