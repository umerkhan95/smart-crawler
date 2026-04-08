"""Query set loaders.

Each loader returns list[BenchmarkQuery]. Loaders are responsible for
setting redact_in_results=True on queries from restricted sources.

- freshqa.py    — Apache-2.0, full traces allowed
- browsecomp.py — encrypted; loader sets redact_in_results=True on every
                  query and asserts the canary string filter
"""
