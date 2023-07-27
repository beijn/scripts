#!python
# pip install beautifulsoup4 pandas

from types import SimpleNamespace as obj

import asyncio

def main():
  import argparse, sys

  p = argparse.ArgumentParser(prog='HS-Bump', description=
    "Scrape the web to yield most uptodate GHC, HSL and Stackage-LTS versions that fit together.")
  p.add_argument('--nix', action='store_true', help=
    "Narrow the search to packages on nixpkgs and output nix package names where possible instead of versions.")
  p.add_argument('--lts', action='store_true', help=
    "Search for a stackage snapshot.")
  p.add_argument('--hls', action='store_true', help=
    "Search for a haskell language server version.")

  args = vars(p.parse_args(sys.argv[1:]))
  print(list(solve(**args))[0])


async def _fetch(url):
  """ Get the url content as a html beautiful soup. """
  import bs4, urllib
  html = await asyncio.get_event_loop().run_in_executor(None, lambda: urllib.request.urlopen(url).read().decode("utf-8"))
  return bs4.BeautifulSoup(html, "html.parser")


async def _fetch_hls_latest():
  import urllib
  url = "https://github.com/haskell/haskell-language-server/releases/latest"
  tag_url = await asyncio.get_event_loop().run_in_executor(None, lambda: urllib.request.urlopen(url).url)  # latest link gets forwarded to respective tag
  return tag_url.split('/')[-1]  # forwarded url tag is latest version


async def _fetch_hls2ghc(version):
  """ @param version = stable | latest, the HLS version for which to query ghc support. Stable is that on nixpkgs.
      @return A dict: for every HLS version all fully supported GHC versions. (No entry if none.) """
  import pandas  # TODO chore: custom table parsing to reduce dependencies
  url = f"https://haskell-language-server.readthedocs.io/en/{version}/support/ghc-version-support.html"
  table = pandas.read_html(str((await _fetch(url)).table))[0]
  return (x:=table)[x['Support status'] == 'full support'].groupby('Last supporting HLS version')['GHC version'].apply(list).to_dict()


async def _fetch_lts2ghc():
  import re
  url = "https://www.stackage.org/"
  lts_lines = (await _fetch(url)).find_all('ul')[2].text.split('\n')[2:]
  def pad(l): return ' '+l if len(l.split('.')[0]) < 2 else l
  return dict((pad((m := re.match(r'LTS (\d+\.\d+) for ghc-(\d+\.\d+\.\d+)', l))[1])
              , [m[2]]) for l in lts_lines if l.strip())


async def _fetch_nix(what):
  packageSet, package = dict(
    ghc = ('nixpkgs#haskell.compiler', r'compiler\.ghc[0-9]+$'),
    hls = ('nixpkgs#haskellPackages', r'haskell-language-server')
  )[what]

  import subprocess, json
  stdout, _ = await (await asyncio.create_subprocess_exec('nix', 'search', packageSet, package,
                '--json', stdout=asyncio.subprocess.PIPE)).communicate()
  return { v['version'] : (packageSet.split('#')[1])+'.'+k.split('.')[-1] for k,v in json.loads(stdout.decode()).items()}



def solve(nix=True, lts=True, hls=True):
  #TODO refactor: so that a new component like lts and hls can be introduced with minimal friction
  import re

  assert lts or hls, "Search for atleast one thing to match with GHC: Stackage LTS, HLS "
  async def fetch_all():
    return await asyncio.gather(
      *([ _fetch_hls2ghc(version = 'stable' if nix else 'latest'),
          _fetch_hls_latest() ] if hls else []),
      *([ _fetch_lts2ghc() ]    if lts else []),
      *([ _fetch_nix('ghc') ]   if nix else []),
      *([ _fetch_nix('hls') ]   if nix and hls else []))

  rest = asyncio.run(fetch_all())

  if hls: hls2ghc, hls_latest, *rest = rest

  if lts: lts2ghc, *rest = rest

  if nix:
    nix2 = {}
    nix2['ghc'], *rest = rest
    if hls:
      nix2['hls'], *rest = rest
      hls_latest = sorted(nix2['hls'])[-1]

  if hls:
    hls2ghc[hls_latest] = hls2ghc['latest']
    del hls2ghc['latest']

  strategy = []
  if hls: strategy += [('hls', hls2ghc)]
  if lts: strategy += [('lts', lts2ghc)]


  def recur(dic, ghcs, strategy):
    (what, it2ghc), *rest_strategy = strategy

    for it in sorted(it2ghc, reverse=True):
      if nix and what in nix2 and it not in nix2[what]: continue

      _dic  = dic | {what:it}
      _ghcs = set(it2ghc[it]) if ghcs=='init' else ghcs & set(it2ghc[it])

      if rest_strategy:
        yield from recur(_dic, _ghcs, rest_strategy)

      if not rest_strategy:
        for ghc in sorted(list(_ghcs), reverse=True):
          if nix and ghc not in nix2['ghc']: continue
          yield _dic | dict(ghc=ghc)


  return recur({}, 'init', strategy)


if __name__ == '__main__': main()
