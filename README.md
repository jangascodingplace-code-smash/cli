# Code Smash CLI

This is a command line interface for the Code Smash API.
It allows you to interact with the API from the command line.

## Requirements
- Python 3.10 or higher
- Poetry or pip

## Installation
1. Clone the repository
    ```bash
    git clone git@github.com:jangascodingplace-code-smash/cli.git
    ```
2. Install the dependencies (pip and poetry are supported)
    ```bash
    pip install -r requirements.txt
    ```
    or
    ```bash
    poetry install --no-dev
    ```
3. Set your personal API token in the environment variable `CODE_SMASH_TOKEN`
    ```bash
    export CODE_SMASH_TOKEN=your_api_token
    ```

## Usage

Apply Task and retrieve Feedback
```bash
python main.py task apply \
  --local-path {{ PATH_TO_THE_PROJECT }} \
  --main-branch-name {{ MAIN_BRANCH_NAME }}
```

This will print the server Response. Here an example output:

```text
Implementation:
The current code provided is written in Python, not C++. To begin developing a C++ command-line To-Do List application, you should start by changing the file type to a .cpp file. Create a basic command-line interface in C++ using standard I/O streams to display menu options for adding, viewing, editing, and deleting tasks.

---
Code Quality:
The code quality cannot be assessed in terms of C++ as it is written in Python. For designing a CLI in C++, focus on clarity, simplicity, and ensure proper commenting for future expansion and readability.

---
Best Practices:
In C++, it's best to use functions to modularize your menu code and follow naming conventions for variables and functions. Make sure to handle input errors gracefully and provide clear instructions to the user. Additionally, using the Standard Template Library (STL) for containers and algorithms will be beneficial for managing tasks.

---
Task is Fulfilled: No.
```
