# deb-github

Build a Debian APT repository from packages on GitHub.

## Usage

Add one line to `/etc/apt/sources.list.d/ibug.list`:

```shell
deb [trusted=yes] https://deb-github.ibugone.com/ stable main
```

Then run the usual `apt update` commands.

## How it works

The core feature lies with [`main.py`](main.py).
It fetches the packages from configured repositories and produce APT indices (`Release` and `Packages` files).
Then along with the [`_redirects`](output/_redirects) file, everything is uploaded to a Cloudflare Pages site.
From this point, Cloudflare Pages will serve the index files, while the `_redirects` file will redirect actual package downloads back to GitHub.

There's a [GitHub Actions workflow](.github/workflows/build.yml) that automates all of these.

## Packages

Indexed repositories are listed in [`config.yml`](config.yml).
