# Contributing

Use Python 3.11 or 3.12. Create a virtual environment, then run:

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
```

Tests use dummy SDL video and audio drivers. Describe behavior changes and tests in pull requests;
include screenshots for visual changes when possible. Never commit API keys, personal configuration,
save games, generated builds, or private data. `.env.example` and `config.example.toml` are safe
templates, not places for credentials. Windows SAPI, external model providers, and native installers
require separate platform-specific testing.

The repository does not yet specify a project license; ask the repository owner before relying on
permission to redistribute or contribute under a particular license. Bundled fonts have their own
licenses in `aivillage/assets/fonts/`.
