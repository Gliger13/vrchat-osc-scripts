# vrchat-osc-scripts installation using Python

## Prerequisites

- [Python](https://www.python.org/)
- [Git](https://git-scm.com/)
- A [Bash](https://www.gnu.org/software/bash/) or compatible shell (e.g. Terminal, Git Bash, WSL, or PowerShell with adjustments)

## Installation (Project Side)

1. Clone the project:
    ```bash
    git clone https://github.com/Gliger13/vrchat-osc-scripts.git
    ```

2. Navigate into the project directory:
    ```bash
    cd vrchat-osc-scripts
    ```

3. Create a virtual Python environment:
    ```bash
    python -m venv .venv
    ```

4. Activate the virtual environment:
    - On Windows:
        ```bash
        .venv\Scripts\activate
        ```
    - On Unix or MacOS:
        ```bash
        source .venv/bin/activate
        ```

5. Install Poetry (Python package management):
    ```bash
    pip install poetry
    ```

6. Install the project dependencies:
    ```bash
    poetry install
    ```

## Usage

Python virtual environment must be always activated to run the script.

## Usage

Run the script with your PiShock credentials provided as environment variables or using .env file:

```bash
PISHOCK_USERNAME="<pishock-username>" \
PISHOCK_API_KEY="<pishock-api-key>" \
PISHOCK_CODE="<pishock-code>" \
python vrchat_osc_scripts/main.py
```

Next steps:
- [Install it from unit site](installation-unity.md)
- [Configuration](configuration.md)
