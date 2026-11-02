# Contributing

Thanks for your interest in improving Defensive Dispatch.

## Reporting bugs and requesting features

Open an [issue](https://github.com/n8xja/DefensiveDispatch/issues) using the bug report or
feature request template. For bugs, include the command you ran, the error output, and your
Python version. **Never paste API keys, Application Passwords or your `.env` file.**

## Making changes

1. Fork the repository and create a branch: `git checkout -b my-change`
2. Set up a development environment:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
3. Make your change and add or update tests in `test_summarize.py`.
4. Run the tests: `pytest -q`
   If you changed the Dockerfile or dependencies, also check the image builds and starts:
   ```bash
   docker build -t defensive-dispatch . && docker run --rm defensive-dispatch --help
   ```
5. Open a pull request describing what changed and why.

## Guidelines

- Keep the tests offline: stub Claude and WordPress rather than calling them.
- Posts must stay drafts by default, and the no-copied-text check must stay in place.
- Keep dependencies minimal and list any new ones in `requirements.txt`.
- Follow the existing code style (PEP 8, type hints where helpful).
