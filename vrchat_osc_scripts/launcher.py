"""Simple script with error handling to prevent the .exe from exiting immediately on error."""

try:
    import os

    import main

    # Strange windows thing to support console colors
    # Ignore Bandit warnings since we spawn the simplest possible process
    # to clear the just-created Command Prompt window.
    # B605: Starting a process with a shell. B607: Starting a process with a partial executable path
    os.system("cls")  # nosec B605, B607

    main.main()
except Exception:
    import traceback

    traceback.print_exc()
    input("Oh no, an error! Blame Gliger. Press Enter to exit...")
