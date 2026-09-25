"""Download the 120 KPF benchmark instances and check them against data/instances_manifest.csv.

The instances are those of Capobianco et al. (2022). They are taken from the archive kpf_soco_instances.zip of a
public repository, at the commit recorded in data/instances_source.json, and they are not redistributed here. The
archive and every instance file are checked by SHA-256.

    python scripts/download_instances.py                       # download the archive
    python scripts/download_instances.py --archive PATH.zip    # use a local copy of the archive

The files are written to instances/ with the layout of the archive (instances/kpf_soco_instances/<set>/<n>/...).
Only the Python standard library is used.
"""
import argparse
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kpf_instance import Instance, read_manifest, sha256_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    source = json.loads((ROOT / "data" / "instances_source.json").read_text())
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--archive", type=Path, help="local copy of kpf_soco_instances.zip")
    ap.add_argument("--dest", type=Path, default=ROOT / "instances", help="output folder (default: instances/)")
    args = ap.parse_args()

    if args.archive:
        data = args.archive.read_bytes()
    else:
        print(f"downloading {source['url']}")
        with urllib.request.urlopen(source["url"], timeout=300) as resp:
            data = resp.read()
    digest = sha256_bytes(data)
    if digest != source["archive_sha256"]:
        sys.exit(f"the archive has SHA-256 {digest}; expected {source['archive_sha256']}")
    print(f"archive: {len(data)} bytes, SHA-256 verified")

    manifest = read_manifest(ROOT / "data" / "instances_manifest.csv")
    failed = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name, row in manifest.items():
            content = zf.read(row["file"])
            if sha256_bytes(content) != row["sha256"]:
                failed.append(f"{name}: SHA-256 differs from the manifest")
                continue
            out = args.dest / row["file"]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(content)
            ins = Instance.read(out, name)
            if (ins.n, ins.l, ins.capacity) != (int(row["n"]), int(row["pairs"]), int(row["capacity"])):
                failed.append(f"{name}: n, pairs or capacity differ from the manifest")
        readme = args.dest / source["readme"]
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_bytes(zf.read(source["readme"]))
    if failed:
        print("\n".join(failed))
        sys.exit(f"{len(failed)} of {len(manifest)} instances failed")
    print(f"{len(manifest)} instances written to {args.dest} and verified")


if __name__ == "__main__":
    main()
