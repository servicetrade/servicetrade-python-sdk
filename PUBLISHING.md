# Publishing to PyPI

This package is published to PyPI automatically via GitHub Actions using [trusted publishing](https://docs.pypi.org/trusted-publishers/) (no API tokens required).

## Steps

1. Update the version in `pyproject.toml`:

   ```toml
   version = "1.1.0"
   ```

2. Commit the version bump:

   ```bash
   git commit -am "Bump version to 1.1.0"
   git push
   ```

3. Tag the release and push the tag:

   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

   Pushing the `v*` tag triggers the **Publish to PyPI** workflow, which builds the package and publishes it.

4. Monitor the workflow run at [Actions](https://github.com/servicetrade/servicetrade-python-sdk/actions/workflows/publish.yml).

## Prerequisites

The GitHub repo must be configured as a [trusted publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) on PyPI:

- **PyPI project name:** `servicetrade`
- **Owner:** `servicetrade`
- **Repository:** `servicetrade-python-sdk`
- **Workflow:** `publish.yml`
