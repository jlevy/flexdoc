## Installing uv and Python

This project is set up to use [**uv**](https://docs.astral.sh/uv/), the new package
manager for Python. `uv` replaces traditional use of `pyenv`, `pipx`, `poetry`, `pip`,
etc. This is a quick cheat sheet on that:

On macOS or Linux, if you don’t have `uv` installed, a quick way to install it:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On macOS, if you prefer [brew](https://brew.sh/), you can install or upgrade uv with:

```shell
brew update
brew install uv
```

See [uv’s docs](https://docs.astral.sh/uv/getting-started/installation/) for more
installation methods and platforms.

Now you can use uv to install a current Python environment:

```shell
uv python install 3.13 # Or pick another version.
```

flexdoc supports CPython 3.11–3.14 with the GIL, not free-threaded 3.14t; use
`--python 3.13` or a GIL 3.14 (`uv python find 3.14` may resolve to 3.14t).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
