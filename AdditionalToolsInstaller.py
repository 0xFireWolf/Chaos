#
# MARK: - Define the interface of installing additional tools
#


class AdditionalToolsInstaller:
    """
    An extension point that developers can use to install additional tools needed to build their project

    Each method below corresponds to a supported host system. Subclass this class and override only the
    methods for host systems on which additional tools are required; the default implementations are
    no-ops that simply announce that nothing needs to be installed.
    """

    def macos(self) -> None:
        """
        Install additional tools needed to build the project on macOS

        The default implementation is a no-op. Override this method to install project-specific tools.
        """
        print("This project does not require any additional development tools on macOS.")

    def ubuntu(self) -> None:
        """
        Install additional tools needed to build the project on Ubuntu

        The default implementation is a no-op. Override this method to install project-specific tools.
        """
        print("This project does not require any additional development tools on Ubuntu.")

    def windows(self) -> None:
        """
        Install additional tools needed to build the project on Windows

        The default implementation is a no-op. Override this method to install project-specific tools.
        """
        print("This project does not require any additional development tools on Windows.")

    def freebsd(self) -> None:
        """
        Install additional tools needed to build the project on FreeBSD

        The default implementation is a no-op. Override this method to install project-specific tools.
        """
        print("This project does not require any additional development tools on FreeBSD.")
