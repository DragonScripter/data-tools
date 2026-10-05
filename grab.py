"""grab.py - pull public data and save it as a CSV.

Works with:
  - UCI shortcuts, IDs, or names     python grab.py mpg
  - UCI dataset page links           python grab.py https://archive.ics.uci.edu/dataset/9/auto+mpg
  - direct CSV links                 python grab.py https://example.com/data.csv
  - webpages with tables             python grab.py https://en.wikipedia.org/wiki/... gdp.csv 2

Usage:
    python grab.py <source> [output.csv] [table_number]
(table_number is optional. Webpages can have many tables; by default the biggest one is used.
The script lists all tables it finds so you can pick another number.)
"""
import io
import re
import sys
import urllib.request
import pandas as pd

# Shortcut name -> UCI dataset ID.
SHORTCUTS = {
    "mpg":      9,    # Auto MPG
    "wine":     186,  # Wine Quality
    "iris":     53,   # Iris
    "heart":    45,   # Heart Disease
    "abalone":  1,    # Abalone
    "concrete": 165,  # Concrete Compressive Strength
    "energy":   242,  # Energy Efficiency
    "realestate": 477,  # Real Estate Valuation
}


def from_uci(key):
    """Get a UCI dataset by ID or name. Returns (DataFrame, name)."""
    from ucimlrepo import fetch_ucirepo  # pip install ucimlrepo
    ds = fetch_ucirepo(id=int(key)) if str(key).isdigit() else fetch_ucirepo(name=str(key))
    # UCI splits data into ids / features / targets; put them back together
    parts = [ds.data.ids, ds.data.features, ds.data.targets]
    df = pd.concat([p for p in parts if p is not None], axis=1)
    print(f"Dataset: {ds.metadata.name} ({ds.metadata.num_instances} rows)")
    return df, ds.metadata.name.lower().replace(" ", "_")


def download(url):
    """Download a URL, sending a browser-style header so sites don't block us."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (data-tools grab.py)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def from_url(url, table=None):
    """Get data from a CSV link or a webpage table. Returns (DataFrame, name)."""
    content = download(url)
    if url.lower().split("?")[0].endswith(".csv"):
        return pd.read_csv(io.BytesIO(content)), "data"
    tables = pd.read_html(io.BytesIO(content))
    print(f"Found {len(tables)} table(s) on the page:")
    for i, t in enumerate(tables):
        cols = [" ".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in t.columns]
        print(f"  #{i}: {t.shape[0]} rows x {t.shape[1]} cols  {cols[:4]}")
    if table is None:  # default: the biggest table
        table = max(range(len(tables)), key=lambda i: tables[i].size)
    print(f"Using #{table}")
    df = tables[table]
    if isinstance(df.columns, pd.MultiIndex):  # flatten two-row headers
        df.columns = [" ".join(dict.fromkeys(map(str, c))) for c in df.columns]
    return df, "data"


def grab(source, out=None, table=None):
    """Download data from a UCI shortcut/ID/name or a URL and save it as a CSV."""
    source = str(source)
    try:
        uci_page = re.search(r"archive\.ics\.uci\.edu/dataset/(\d+)", source)
        if uci_page:                                  # UCI page link -> use its ID
            df, name = from_uci(uci_page.group(1))
        elif source.startswith("http"):               # any other link
            df, name = from_url(source, table)
        else:                                         # shortcut, ID, or name
            df, name = from_uci(SHORTCUTS.get(source.lower(), source))
    except Exception as e:
        print(f"Couldn't get data for '{source}'\n  {e}")
        return None

    out = out or name + ".csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows x {len(df.columns)} columns to {out}")
    print(df.head())
    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("Shortcuts:", ", ".join(SHORTCUTS))
        sys.exit()
    grab(sys.argv[1],
         sys.argv[2] if len(sys.argv) > 2 else None,
         int(sys.argv[3]) if len(sys.argv) > 3 else None)