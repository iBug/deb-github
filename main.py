#!/usr/bin/python3

import io
import os
import requests
import shutil
import subprocess
import sys
import traceback
import yaml


headers = {}
if "GITHUB_TOEKN" in os.environ:
    headers["Authorization"] = "token " + os.environ["GITHUB_TOKEN"]

with open("config.yml", "r") as f:
    config = yaml.load(f)

output_dir = config["output_dir"]
suite = config["suite"]
component = config["component"]
architectures = config["architectures"]
repositories = config["repositories"]

pool_root = os.path.join(output_dir, "pool", component)
release_dir = os.path.join(output_dir, "dists", suite)

os.makedirs(release_dir, exist_ok=True)

# Source all packages
packages_file = open(os.path.join(release_dir, "Packages"), "w")
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
        # In CI with limited disk space, process repositories one by one
        if "CI" in os.environ:
            subprocess.run(["dpkg-scanpackages", "--multiversion", "."],
                stdin=subprocess.DEVNULL, stdout=packages_file,
                cwd=output_dir, check=True)
            shutil.rmtree(pool_root)
    except Exception as e:
        traceback.print_exc()

if "CI" not in os.environ:
    subprocess.run(["dpkg-scanpackages", "--multiversion", "."],
        stdin=subprocess.DEVNULL, stdout=packages_file,
        cwd=output_dir, check=True)
packages_file.close()

# Split the "Packages" file by architecture
try:
    packages = {}
    for arch in architectures:
        arch_dir = os.path.join(release_dir, component, f"binary-{arch}")
        os.makedirs(arch_dir, exist_ok=True)
        packages[arch] = open(os.path.join(arch_dir, "Packages"), "w")

    buf = []
    arch = None
    with open(packages_file.name, "r") as f:
        for line in f:
            if not line.strip():
                print("".join(buf), file=packages[arch])
                buf = []
                arch = None
                continue
            buf.append(line)
            if line.startswith("Architecture:"):
                arch = line.split()[1].strip()
finally:
    for f in packages.values():
        f.close()

# Generate the "Release" file
with open(os.path.join(release_dir, "Release"), "wb") as f:
    subprocess.run(["apt-ftparchive", "-c", f"{suite}.conf", "release", output_dir], stdin=subprocess.DEVNULL, stdout=f, check=True)
