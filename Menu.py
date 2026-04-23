#
# MARK: - Command Line Menu Support
#

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from .Utilities import clear_console


# Represents an item in a menu
@dataclass
class MenuItem:
    # The human-readable title of the menu item
    title: str
    # A callback function that will be invoked when users select this menu item
    handler: Callable[[], None] | None


# Represents a menu that lists user-selectable items
class Menu:
    def __init__(self, title: str = "") -> None:
        """
        Initialize a menu with the given title
        :param title: The human-readable title of the menu
        """
        self.title = title
        self.items: list[MenuItem] = []
        # A menu item is selectable if it has a non-null handler
        # Such a menu item also has a numbered index that users can enter to select it
        # The index map associates the numbered index with the list index of each selectable menu item
        # This map is populated by `build_index_map` before the menu can be rendered or selected
        self.index_map: dict[int, int] = {}

    def add_item(self, title: str, handler: Callable[[], None] | None = None) -> None:
        """
        Add a menu item with the given title
        :param title: The human-readable title of the menu item
        :param handler: A callback function that will be invoked when users select this menu
        """
        self.items.append(MenuItem(title, handler))

    def add_submenu(self, title: str, submenu: Menu, handler: Callable[[Menu], None]) -> None:
        """
        Add a menu item with the given title and associate it with the given submenu
        :param title: The human-readable title of the menu item
        :param submenu: The submenu to associate with the newly created menu item
        :param handler: A callback function that will be invoked to render the submenu and handle user interactions in the submenu
        """
        self.add_item(title, lambda: handler(submenu))

    def add_separator(self) -> None:
        """
        Add a separator to the menu
        """
        self.add_item("", None)

    def build_index_map(self) -> None:
        """
        Populate the index map used by `render` and `select`

        This must be called before the menu can be rendered or a selection can be made.
        `interact` calls this automatically before entering its main loop.
        """
        self.index_map = {}
        numeric_index = 0
        for list_index, item in enumerate(self.items):
            if item.handler is not None:
                self.index_map[numeric_index] = list_index
                numeric_index += 1

    def render(self) -> None:
        """
        Render the menu

        `build_index_map` must have been called prior to invoking this method.
        """
        print()
        print(self.title)
        print()
        numeric_index = 0
        for item in self.items:
            if item.handler is None:
                # Non-selectable menu item
                print(item.title)
            else:
                # Selectable menu item
                print(f"[{numeric_index:02}] {item.title}")
                numeric_index += 1
        print()

    def select(self, index: int) -> None:
        """
        Select the menu item that has the given index
        :param index: The index of a selectable menu item
        :raise KeyError: if the given index is not associated with any selectable menu item.
        """
        list_index = self.index_map[index]
        self.items[list_index].handler()

    @staticmethod
    def interact(menu: Menu) -> None:
        """
        The default handler for interacting with menus
        :param menu: A menu to interact with
        """
        menu.build_index_map()
        while True:
            clear_console()
            menu.render()
            print("Press Ctrl-C or Ctrl-D to exit from the current menu.")
            # Parse and validate the user input
            # Note that handler exceptions are intentionally not caught here so that they propagate to the caller
            try:
                option = int(input("Input the number and press ENTER: "))
            except ValueError:
                print("Not a number! Please try again.")
                input("Press Enter to continue...")
                continue
            except (KeyboardInterrupt, EOFError):
                break
            if option not in menu.index_map:
                print("The option number you entered is not valid.")
                input("Press Enter to continue...")
                continue
            # Invoke the handler associated with the selected menu item
            menu.select(option)
            print()
            input("Press Enter to continue...")