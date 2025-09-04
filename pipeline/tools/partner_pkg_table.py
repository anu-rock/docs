"""This script populates the Python integrations landing page at.

oss/python/integrations/providers

Usage (from repo root):
```
uv sync --group test

uv run python pipeline/tools/partner_pkg_table.py
```
"""

import glob
from pathlib import Path

import requests
import yaml

#################
# CONFIGURATION #
#################

# packages to ignore / exclude from the table
IGNORE_PACKGAGES = {
    # top-level packages
    "langchain-core",
    "langchain-text-splitters",
    "langchain",
    "langchain-community",
    "langchain-experimental",
    "langchain-cli",
    "langchain-tests",
    # integration packages that don't have a provider index
    # do NOT add to these. These were merged before having a
    # provider index was required
    # can remove these once they have a provider index
    "langchain-yt-dlp",
    # TODO: add pages for these providers
    "langchain-recallio",
}

#####################
# END CONFIGURATION #
#####################

DOCS_DIR = Path(__file__).parents[2]
PACKAGE_YML = "https://raw.githubusercontent.com/langchain-ai/langchain/refs/heads/master/libs/packages.yml"

# for now, only include packages that are in the langchain-ai org
# because we don't have a policy for inclusion in this table yet,
# and including all packages will make the list too long


def _get_type(package: dict) -> str:
    if package["name"] in IGNORE_PACKGAGES:
        return "ignore"
    if package["repo"] == "langchain-ai/langchain":
        return "B"
    if package["repo"].startswith("langchain-ai/"):
        return "C"
    return "D"


def _enrich_package(p: dict) -> dict | None:
    p["name_short"] = p["name"].removeprefix("langchain-")
    p["name_title"] = p.get("name_title") or p["name_short"].title().replace(
        "-", " "
    ).replace("db", "DB").replace("Db", "DB").replace("ai", "AI").replace("Ai", "AI")
    p["type"] = _get_type(p)

    if p["type"] == "ignore":
        return None

    p["js_exists"] = bool(p.get("js"))
    custom_provider_page = p.get("provider_page")
    default_provider_page = f"/oss/integrations/providers/{p['name_short']}/"
    default_provider_page_exists = bool(
        glob.glob(
            str(DOCS_DIR / f"src/oss/python/integrations/providers/{p['name_short']}.*")
        )
    )
    if custom_provider_page:
        p["provider_page"] = f"/oss/integrations/providers/{custom_provider_page}"
    elif default_provider_page_exists:
        p["provider_page"] = default_provider_page
    else:
        msg = (
            f"Provider page not found for {p['name_short']}. "
            f"Please add one at oss/integrations/providers/{p['name_short']}.{{mdx,ipynb}}"
        )
        raise ValueError(msg)

    if p["type"] in ("B", "C"):
        p["package_url"] = (
            f"https://python.langchain.com/api_reference/{p['name_short'].replace('-', '_')}/"
        )
    else:
        p["package_url"] = f"https://pypi.org/project/{p['name']}/"

    return p


# Load package registry
registry_resp = requests.get(PACKAGE_YML, timeout=10)
registry_resp.raise_for_status()

data = yaml.safe_load(registry_resp.text)

packages_n = [_enrich_package(p) for p in data["packages"]]
packages = [p for p in packages_n if p is not None]

# sort by downloads
packages_sorted = sorted(packages, key=lambda p: p.get("downloads", 0), reverse=True)


def package_row(p: dict) -> str:
    js = "✅" if p["js_exists"] else "❌"
    link = p["provider_page"]
    title = p["name_title"]
    provider = f"[{title}]({link})" if link else title
    return (
        f"| {provider} | [{p['name']}]({p['package_url']}) | "
        f"![Downloads](https://static.pepy.tech/badge/{p['name']}/month) | "
        f"![PyPI - Version](https://img.shields.io/pypi/v/{p['name']}?style=flat-square&label=%20&color=orange) | "
        f"{js} |"
    )


def table() -> str:
    header = """| Provider | Package | Downloads | Latest | [JS](https://js.langchain.com/docs/integrations/platforms/) |
| :--- | :---: | :---: | :---: | :---: |
"""
    return header + "\n".join(package_row(p) for p in packages_sorted)


def doc() -> str:
    return f"""\
---
title: Integration packages
---

<Info>

If you'd like to contribute an integration, see [Contributing integrations](/oss/integrations/contributing).

</Info>

## Integration packages

These providers have standalone `langchain-{{provider}}` packages for improved versioning, dependency management and testing.

{table()}

## All providers

Click [here](/oss/integrations/providers/all_providers) to see all providers or search
for a provider using the search field.

"""


if __name__ == "__main__":
    output_dir = Path() / "src" / "oss" / "python" / "integrations" / "providers"
    with open(output_dir / "index.mdx", "w") as f:
        f.write(doc())
