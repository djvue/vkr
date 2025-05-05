import asyncio
import sys

import datasets
import os
import aiohttp
import aiohttp_retry
from typing import Tuple, Optional

import psutil
import aiochan as ac
import aiopath
from tqdm import tqdm
from concurrent.futures import CancelledError

CONCURRENCY = 16
CHAN_BATCH_SIZE = 100
DATA_DIR = "../data"

def dump_memory():
    # Process.memory_info is expressed in bytes, so convert to megabytes
    print(f"RAM used: {psutil.Process().memory_info().rss / (1024 * 1024):.2f} MB")


async def check(row: tuple) -> Tuple[bool, Optional[aiopath.AsyncPath]]:
    repo_name, revision_id = row

    download_path = f"{DATA_DIR}/repo_archives/{revision_id}.tar.gz"

    f = aiopath.AsyncPath(download_path)

    if await f.exists():
        return True, f

    await f.parent.mkdir(parents=True, exist_ok=True)

    #os.makedirs(os.path.dirname(download_path), exist_ok=True)
    #print(f"RAM used: {psutil.Process().memory_info().rss / (1024 * 1024):.2f} MB")

    return False, f


async def download(client: aiohttp_retry.RetryClient, row: tuple, f: aiopath.AsyncPath) -> Tuple[str, dict]:
    repo_name, revision_id = row

    url = f"https://github.com/{repo_name}/archive/{revision_id}.tar.gz"

    try:
        async with client.get(url) as resp:
            if resp.status != 200:
                return "download_wrong_status", {'status': resp.status}
            #print("check length", resp.content_length, resp.headers.get('content-length', None))
            #if resp.content_length is not None and resp.content_length > 10 * 1024 * 1024:
            #    return "download_big", {'size': resp.content_length}

            binary_data = await resp.read()

            await f.write_bytes(binary_data)

            return "download_ok", {}
    except asyncio.TimeoutError:
        return "download_timeout", {}
            

async def producer(in_ch: ac.Chan, ds: datasets.Dataset, ds_len: int) -> None:
    batch = []
    size = 0
    for row in ds:
        size += 1
        batch.append((row['repo_name'], row['revision_id']))
        if len(batch) == CHAN_BATCH_SIZE:
            await in_ch.put(batch)
            batch = []

    if len(batch) > 0:
        await in_ch.put(batch)

    in_ch.close()

async def consumer(in_ch: ac.Chan, out_ch: ac.Chan, consumer_finished_ch: ac.Chan, client: aiohttp_retry.RetryClient) -> None:
    async for batch in in_ch:
        for row in batch:
            ok, f = await check(row)
            if ok:
                await out_ch.put(("check_ok", {}))
                continue
            result, meta = await download(client, row, f)
            if result != "download_ok":
                await out_ch.put((result, meta))
                continue
            await out_ch.put(("processed", {}))

    await consumer_finished_ch.get()


async def monitoring(out_ch: ac.Chan, monitoring_finished_ch: ac.Chan, ds_len: int) -> None:
    with tqdm(total=ds_len) as pbar:
        check_ok = 0
        processed = 0
        download_wrong_status = 0
        download_429 = 0
        download_404 = 0
        download_timeout = 0
        #download_big = 0
        last_error = ""

        async for out in out_ch:
            result, meta = out

            if result == "check_ok":
                check_ok += 1
            elif result == "processed":
                processed += 1
            elif result == "download_timeout":
                download_timeout += 1
            #elif result == "download_big":
            #    download_big += 1
            #    last_error = f"download big size {meta['size']}"
            elif result == "download_wrong_status":
                if meta['status'] == 404:
                    download_404 += 1
                elif meta['status'] == 429:
                    download_429 += 1
                else:
                    download_wrong_status += 1
                    last_error = f"download wrong status {meta['status']}"

            pbar.update(1)
            pbar.set_postfix(
                check_ok=check_ok,
                processed=processed,
                download_wrong_status=download_wrong_status,
                #download_big=download_big,
                download_404=download_404,
                download_429=download_429,
                download_timeout=download_timeout,
                last_error=last_error,
            )

        await monitoring_finished_ch.get()

async def download_by_batches(ds: datasets.Dataset, ds_len: int) -> None:
    in_ch = ac.Chan(CONCURRENCY)
    out_ch = ac.Chan(CONCURRENCY)

    ac.go(producer(in_ch, ds, ds_len))

    monitoring_finished_ch = ac.Chan(1).add(True).close()
    ac.go(monitoring(out_ch, monitoring_finished_ch, ds_len))

    async with aiohttp_retry.RetryClient(
        retry_options=aiohttp_retry.ExponentialRetry(attempts=2, statuses=[500, 429]),
        timeout=aiohttp.ClientTimeout(total=10)
    ) as client:
        consumer_finished_ch = ac.Chan(CONCURRENCY)
        for i in range(CONCURRENCY):
            await consumer_finished_ch.put(True)
            ac.go(consumer(in_ch, out_ch, consumer_finished_ch, client))
        consumer_finished_ch.close()

        await in_ch.join()
        await consumer_finished_ch.join()
        out_ch.close()
        await monitoring_finished_ch.join()

async def run(skip_first: int):
    print("Loading dataset")

    source_ds = datasets.load_from_disk('data/repo_names_ds')

    source_ds_len = len(source_ds)

    print("Skipping first "+str(skip_first))

    print("Scraping dataset, len "+str(source_ds_len-skip_first))

    source_ds = source_ds.skip(skip_first)

    try:
        await download_by_batches(source_ds, source_ds_len - skip_first)
    except (CancelledError, asyncio.exceptions.CancelledError) as e:
        print(f"\nCancelled {e}")

if __name__ == "__main__":
    skip_first = 0
    if len(sys.argv) > 1:
        skip_first = int(sys.argv[1])

    asyncio.run(run(skip_first))

