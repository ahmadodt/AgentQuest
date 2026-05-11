import argparse
import json
import os
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


ENDPOINTS = {
    "monsters": "https://api.open5e.com/v1/monsters/",
    "spells": "https://api.open5e.com/v1/spells/",
    "weapons": "https://api.open5e.com/v1/weapons/",
    "armor": "https://api.open5e.com/v1/armor/",
    "classes": "https://api.open5e.com/v1/classes/",
    "conditions": "https://api.open5e.com/v1/conditions/",
    "feats": "https://api.open5e.com/v1/feats/",
    "magicitems": "https://api.open5e.com/v1/magicitems/",
}


def fetch_json(url):
    request = Request(url, headers={"User-Agent": "AgentQuest/0.1"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download_endpoint(name, url, out_dir, max_pages=None, sleep_seconds=0.2):
    print(f"Downloading {name} from {url}")

    results = []
    page_count = 0
    next_url = url

    while next_url:
        page_count += 1

        if max_pages is not None and page_count > max_pages:
            break

        print(f"  page {page_count}: {next_url}")

        try:
            payload = fetch_json(next_url)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Failed downloading {name} page {page_count}: {exc}") from exc

        results.extend(payload.get("results", []))
        next_url = payload.get("next")

        time.sleep(sleep_seconds)

    output = {
        "source": "open5e",
        "endpoint": name,
        "downloaded_pages": page_count,
        "count": len(results),
        "results": results,
    }

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{name}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(results)} records to {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=os.path.join("data", "raw", "open5e"))
    parser.add_argument("--endpoint", choices=list(ENDPOINTS.keys()) + ["all"], default="all")
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    selected = ENDPOINTS
    if args.endpoint != "all":
        selected = {args.endpoint: ENDPOINTS[args.endpoint]}

    for name, url in selected.items():
        download_endpoint(
            name=name,
            url=url,
            out_dir=args.out_dir,
            max_pages=args.max_pages,
        )


if __name__ == "__main__":
    main()