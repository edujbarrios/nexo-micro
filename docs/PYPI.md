# Shipping NEXO Micro to PyPI

## Prerequisites

- The GitHub repository is public and the `main` branch is green.
- Own the package name `nexo-micro` on PyPI (a pending publisher **does not reserve the name**).
- `pyproject.toml` has the intended unique version. Never republish the same version; increment it for updates.
- Check project metadata and README for truthful limitations and MIT attribution.

## Validate the artifacts locally

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src tests examples
python -m build
python -m twine check dist/*
```

If using isolated Python builds, verify `pip install dist/*.whl` in a clean venv. CI does so on every push.

## Configure secure publishing (one-time actions by owner)

1. On GitHub go to **Settings → Environments → New environment** and create **`pypi`**. Strongly recommend **required reviewers** and restricting deployment to protected tags/releases.
2. On [pypi.org](https://pypi.org/), log into your account, then add a **Trusted Publisher** (pending publisher if the project does not yet exist):
   - PyPI project name: `nexo-micro`
   - Owner: `edujbarrios`
   - Repository: `nexo-micro`
   - Workflow: **`release.yml`**
   - Environment: **`pypi`**
3. Review the GitHub Actions workflow `.github/workflows/release.yml`. It uses short-lived OIDC tokens (`id-token: write`) only in the upload job; **no PyPI API token or secret is required**.
4. Protect release tags or use required reviewers on `pypi` before creating a release.

See [official PyPI Trusted Publishing docs](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

## First release

1. Merge all changes and wait for passing CI.
2. Create a **GitHub Release** tagged **`v0.1.0`**, pointing to the commit you want to publish. Make it a *normal*, not pre-release, publication.
3. `release.yml` re-runs tests, checks tag vs package version, builds wheel+sdist, performs `twine check`, installs the wheel and publishes both artifacts to PyPI after `pypi` environment approval.
4. Confirm that `https://pypi.org/project/nexo-micro/0.1.0/` exists and try `pip install nexo-micro` in a clean environment.

**The GitHub repository does not publish by itself.** A Release and the owner-managed PyPI + GitHub setup are required. Do not create release tags until publishing is desired.

## Subsequent releases

Increment `project.version` in `pyproject.toml` and `__version__` in `src/nexo_micro/__init__.py`, update CHANGELOG, verify CI, then publish an identically versioned GitHub Release tag. PyPI releases are immutable.
