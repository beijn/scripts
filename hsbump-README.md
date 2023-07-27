# Determine Haskell development software version bumps

Scrape the web to determine the most uptodate versions of different Haskell development software that works together.

## Usage

- as a standalone CLI script: `curl 'https://raw.githubusercontent.com/beijn/scripts/main/hsbump.py' | python - --lts --hls --nix`
- as a python library module:
  - `mkdir -p util && wget 'https://raw.githubusercontent.com/beijn/scripts/main/hsbump.py' -P util`
  - `from utils.hsbump import solve; versions = solve(lts=True, hls=True, nix=True)`

## Featured Software
- _Haskell Language Server_ (`--hls`): include search for a latest compatible HLS
- _Stackage LTS_ (`--lts`): include search for a latest compatible stackage LTS snaptshot


## Modes
- _default_: Return the highest compatible versions without checking their availability in any repo.
- _`--nix`_: Constrain search to nixpkgs (provided by your environment) and return nix package names.

## How it works

- web scraping with `urllib` and `beautifulsoup4`
- nix cli queries with `asyncio.create_subprocess_exec` (similar to `subprocess`)
- asynchronous IO for the above two with `asyncio`
- data extraction `re` and `pandas`
- cli interface with `argparse`

- compatibility of softwares is defined by their GHC version support
- its quite easy to integrate new softwares to check for as the core resolution algorithm is abstracted over them+
  - decoupling can be improved a lot

## Requirements

- python libraries `beautifulsoup4 pandas` for web scraping
- in `nix` mode: modern nix cli