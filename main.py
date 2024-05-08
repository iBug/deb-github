#!/usr/bin/python3

import io
import os
import requests
import shutil
import subprocess
import sys
import traceback


headers = {}
if "GITHUB_TOEKN" in os.environ:
    headers["Authorization"] = "token " + os.environ["GITHUB_TOKEN"]


output_dir = "output"
pool_root = os.path.join(output_dir, "pool")
repositories = [
    "coder/code-server",
    "jgm/pandoc",
]
packages_file = open(os.path.join(output_dir, "Packages.new"), "w")


os.makedirs(output_dir, exist_ok=True)
for repo in repositories:
    print(f"{repo}:", file=sys.stderr)
    try:
        latest = requests.get(f"https://api.github.com/repos/{repo}/releases/latest", headers=headers).json()
        tag_name = latest["tag_name"]
        for asset in latest["assets"]:
            if not asset["name"].endswith(".deb"):
                print(f"  {asset['name']}: skipped", file=sys.stderr)
                continue
            print(f"  {asset['name']}: download", file=sys.stderr)
            local_dir = os.path.join(pool_root, repo, tag_name)
            local_name = os.path.join(local_dir, asset["name"])

            os.makedirs(local_dir, exist_ok=True)
            if os.path.isfile(local_name):
                print(f"    {local_name} already exists", file=sys.stderr)
                continue

            resp = requests.get(asset["browser_download_url"], stream=True)
            if not resp.ok:
                continue
            with open(local_name, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
        subprocess.run(["dpkg-scanpackages", "--multiversion", "."],
            stdin=subprocess.DEVNULL, stdout=packages_file,
            cwd=output_dir, check=True)
        if "CI" in os.environ:
            shutil.rmtree(pool_root)
    except Exception as e:
        traceback.print_exc()

os.rename(packages_file.name, os.path.join(output_dir, "Packages"))
