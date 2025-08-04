"""Simple script with error handling to prevent the .exe from exiting immediately on error."""

try:
    import main

    main.main()
except Exception:
    import traceback

    traceback.print_exc()
    input("Oh no, an error! Blame Gliger. Press Enter to exit...")
