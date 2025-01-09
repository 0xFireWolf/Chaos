# Chaos

A control center for CMake + Conan + C++20 projects.

## Dependencies

Chaos is written in Python 3 and requires the following packages:
- distro: `pip install distro`
- requests: `pip install requests`

to install packages globally, in case `pip` does not allow it (e.g., on Ubuntu), install them via `apt`:
```bash
sudo apt install python3-distro python3-requests
```

## Usage
1. Install all the required tools:
   ```
   > 02 (Press Enter)
   ```
2. Install a compiler
   Example: GCC 14
   ```
   > 03 (Press Enter)
   > 04 (Press Enter)
   ```
4. **Select a compiler toolchain**
   Example Toolchain: x86-64, GCC 14, Default, Ubuntu, APT    
   ```
   > 05 (Press Enter)
   > 36 (Press Enter)
   ```
6. Build (and run tests)
   Example: Rebuild and run all tests (DEBUG)
   ```
   > 08 (Press Enter)
   ```
