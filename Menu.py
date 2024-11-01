#
# MARK: - Command Line Menu Support
#

from __future__ import annotations
from typing import Callable

# Represents an item in a menu
class MenuItem:
    def __init__(self, identifier: int, title: str, handler: Callable[[], None] | None) -> None:
        """
        Initialize a menu item with the given title and handler
        :param identifier: The unique identifier of the menu item
        :param title: The human-readable title of the menu item
        :param handler: A callback function that will be invoked when users select this menu item
        """
        self.identifier = identifier
        self.title = title
        self.handler = handler


# Represents a menu that lists user-selectable items
class Menu:
    def __init__(self, title: str = "") -> None:
        """
        Initialize a menu with the given title
        :param title: The human-readable title of the menu
        """
        self.title = title
        self.items: list[MenuItem] = []
        # Each menu item has a unique identifier, which also serves as the index into `self.items`
        # The identifier tracker keeps track of the next available slot in `self.items`
        self.identifier_tracker = 0
        # A menu item is selectable if it has a non-null handler
        # Such a menu item also has a numbered index that users can enter to select it
        # The index map associates the numbered index with the identifier of each selectable menu item
        # This map is updated by the `render` function that allocates a numbered index for each selectable menu item
        self.index_map: dict[int, int] = {}

    def add_item(self, title: str, handler: Callable[[], None] | None = None) -> None:
        """
        Add a menu item with the given title
        :param title: The human-readable title of the menu item
        :param handler: A callback function that will be invoked when users select this menu
        """
        self.items.append(MenuItem(self.identifier_tracker, title, handler))
        self.identifier_tracker += 1

    def add_submenu(self, title: str, submenu: Menu, handler: Callable[[Menu], None]) -> None:
        """
        Add a menu item with the given title and associate it with the given submenu
        :param title: The human-readable title of the menu item
        :param submenu: The submenu to associate with the newly created menu item
        :param handler: A callback function that will be invoked to render the submenu and handle user interactions in the submenu
        """
        self.add_item(title, lambda : handler(submenu))

    def add_separator(self) -> None:
        """
        Add a separator to the menu
        """
        self.add_item("", None)

    def build_index_map(self) -> None:
        """
        Build the index map for the non-interactive mode
        """
        index = 0
        for item in self.items:
            if item.handler is not None:
                self.index_map[index] = item.identifier
                index += 1

    def render(self) -> None:
        """
        Render the menu
        """
        print()
        print(self.title)
        print()
        index = 0
        for item in self.items:
            if item.handler is None:
                # Non-selectable menu item
                print(item.title)
            else:
                # Selectable menu item
                print(f"[{index:02}] {item.title}")
                self.index_map[index] = item.identifier
                index += 1
        print()

    def select(self, index: int) -> None:
        """
        Select the menu item that has the given index
        :param index: The index of a selectable menu item
        """
        identifier = self.index_map[index]
        item = self.items[identifier]
        item.handler()
