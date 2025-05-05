import sys
import os

import datasets
import os
import pandas as pd

import psutil

import tarfile
import shutil

DATA_DIR = "/media/hdd_1/vkr/data"
REPOS_DIR = f"{DATA_DIR}/repos"

def dump_memory():
    # Process.memory_info is expressed in bytes, so convert to megabytes
    print(f"RAM used: {psutil.Process().memory_info().rss / (1024 * 1024):.2f} MB")

async def extract_repo_archive(row) -> None:
    repo_name, revision_id = row['repo_name'], row['revision_id']

    download_path = f"{DATA_DIR}/repo_archives/{revision_id}.tar.gz"
    output_path = f"{REPOS_DIR}/{revision_id}"

    if os.path.exists(output_path):
        #shutil.rmtree(output_path)
        return {"status": "exists", "files": []}

    if not os.path.exists(download_path):
        return {"status": "no_archive", "files": []}

    files = []
    prefix = ""
    is_first = True

    try:
        with tarfile.open(download_path, 'r') as t:
            for member in t.getmembers():
                prefix_slash_pos = member.name.find('/')
                prefix = member.name[:prefix_slash_pos]
                name = member.name[prefix_slash_pos+1:]
                if (not name.endswith(".go")
                    and not name.endswith(".mod")
                    and not name.endswith(".sum")):
                    continue
                if name.startswith('vendor/'):
                    continue
                if is_first:
                    if os.path.exists(f"{REPOS_DIR}/{prefix}"):
                        shutil.rmtree(f"{REPOS_DIR}/{prefix}")
                    is_first = False

                files.append(name)
                t.extract(member, REPOS_DIR)
    except tarfile.ReadError:
        return {"status": "invalid_archive", "files": []}

    if len(files) > 0:
        shutil.move(f"{REPOS_DIR}/{prefix}", output_path)

    return {"status": "ok", "files": []}

def run(skip_first: int):
    print("Loading dataset")

    source_ds = datasets.load_from_disk('data/repo_names_ds')

    source_ds_len = len(source_ds)

    print("Skipping first "+str(skip_first))

    print("Extracting archives, remaining "+str(source_ds_len-skip_first))

    source_ds = source_ds.skip(skip_first)#.take(10)

    os.makedirs(REPOS_DIR, exist_ok=True)

    res = source_ds.map(extract_repo_archive, num_proc=32)

    res.save_to_disk('data/repo_extract_status_ds')

if __name__ == "__main__":
    skip_first = 0
    if len(sys.argv) > 1:
        skip_first = int(sys.argv[1])

    run(skip_first)

