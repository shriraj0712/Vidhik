import os
import re
import time
import requests


BASE_URL = "https://indiacode.gov.in"

COLLECTION_ID = "69a0c1fb-7b22-4481-b16a-1dc59b5d02e6"

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "Legal_Dataset",
    "PDFs"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


session = requests.Session()

session.headers.update({
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0"
})


def clean_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def get_acts_page(page):

    url = (
        f"{BASE_URL}/server/api/discover/search/objects"
        f"?size=100"
        f"&page={page}"
        f"&dsoType=ITEM"
        f"&scope={COLLECTION_ID}"
    )

    print(f"\nRequesting page {page + 1}...")

    response = session.get(url, timeout=60)
    response.raise_for_status()

    return response.json()


def find_items(data):

    items = []

    embedded = data.get("_embedded", {})

    search_result = embedded.get("searchResult", {})

    objects = search_result.get(
        "_embedded", {}
    ).get("objects", [])

    for result in objects:

        obj = result.get(
            "_embedded", {}
        ).get("indexableObject")

        if obj:
            items.append(obj)

    return items


def get_total_pages(data):

    embedded = data.get("_embedded", {})

    search_result = embedded.get(
        "searchResult", {}
    )

    page_info = search_result.get(
        "page", {}
    )

    return page_info.get(
        "totalPages"
    )


def get_item(item_uuid):

    url = (
        f"{BASE_URL}/server/api/core/items/"
        f"{item_uuid}"
    )

    response = session.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def get_bundles(item_uuid):

    url = (
        f"{BASE_URL}/server/api/core/items/"
        f"{item_uuid}/bundles"
    )

    response = session.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def find_pdf_bitstream(bundles_data):

    bundles = bundles_data.get(
        "_embedded", {}
    ).get("bundles", [])

    for bundle in bundles:

        bundle_uuid = bundle.get("uuid")

        if not bundle_uuid:
            continue

        url = (
            f"{BASE_URL}/server/api/core/bundles/"
            f"{bundle_uuid}/bitstreams"
        )

        response = session.get(
            url,
            timeout=60
        )

        if response.status_code != 200:
            continue

        data = response.json()

        bitstreams = data.get(
            "_embedded", {}
        ).get("bitstreams", [])

        for bitstream in bitstreams:

            name = bitstream.get(
                "name", ""
            ).lower()

            if name.endswith(".pdf"):
                return bitstream

    return None


def download_pdf(bitstream, filename):

    uuid = bitstream.get("uuid")

    if not uuid:
        return False

    filepath = os.path.join(
        OUTPUT_DIR,
        filename
    )

    # Skip already downloaded files
    if os.path.exists(filepath):

        print(
            "  Already downloaded:",
            filename
        )

        return True

    url = (
        f"{BASE_URL}/server/api/core/"
        f"bitstreams/{uuid}/content"
    )

    print(
        "  Downloading:",
        filename
    )

    response = session.get(
        url,
        stream=True,
        timeout=120
    )

    if response.status_code != 200:

        print(
            "  Download failed:",
            response.status_code
        )

        return False

    with open(
        filepath,
        "wb"
    ) as f:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:
                f.write(chunk)

    return True


def main():

    print()
    print("======================================")
    print(" INDIA CODE CENTRAL ACTS DOWNLOADER")
    print("======================================")

    all_acts = []

    page = 0

    total_pages = None

    while True:

        try:

            data = get_acts_page(page)

            acts = find_items(data)

            if total_pages is None:

                total_pages = get_total_pages(data)

                print(
                    "Total pages:",
                    total_pages
                )

            if not acts:
                print(
                    "No more Acts found."
                )
                break

            print(
                f"Acts found on this page: "
                f"{len(acts)}"
            )

            all_acts.extend(acts)

            page += 1

            # Stop when all pages are collected
            if total_pages is not None:
                if page >= total_pages:
                    break

            time.sleep(0.5)

        except Exception as e:

            print(
                "Error while collecting Acts:",
                e
            )

            break


    # Remove duplicates
    unique_acts = {}

    for act in all_acts:

        uuid = act.get("uuid")

        if uuid:
            unique_acts[uuid] = act


    acts = list(
        unique_acts.values()
    )


    print()
    print("======================================")
    print(
        "TOTAL CENTRAL ACTS FOUND:",
        len(acts)
    )
    print("======================================")
    print()


    downloaded = 0
    skipped = 0
    failed = 0


    for index, act in enumerate(
        acts,
        start=1
    ):

        uuid = act.get("uuid")

        name = (
            act.get("name")
            or f"act_{index}"
        )

        print(
            f"[{index}/{len(acts)}] {name}"
        )

        try:

            item = get_item(uuid)

            act_name = (
                item.get("name")
                or name
            )

            filename = (
                clean_filename(act_name)
                + ".pdf"
            )

            filepath = os.path.join(
                OUTPUT_DIR,
                filename
            )

            # Don't even contact the API if already downloaded
            if os.path.exists(filepath):

                print(
                    "  Already exists."
                )

                skipped += 1

                continue


            bundles = get_bundles(uuid)

            bitstream = find_pdf_bitstream(
                bundles
            )

            if not bitstream:

                print(
                    "  PDF not found."
                )

                failed += 1

                continue


            success = download_pdf(
                bitstream,
                filename
            )

            if success:
                downloaded += 1
            else:
                failed += 1


            # Small delay to avoid hammering the server
            time.sleep(0.5)


        except Exception as e:

            print(
                "  ERROR:",
                e
            )

            failed += 1


    print()
    print("======================================")
    print(" DOWNLOAD COMPLETED")
    print("======================================")
    print(
        "Total Acts:",
        len(acts)
    )
    print(
        "Downloaded:",
        downloaded
    )
    print(
        "Already existed:",
        skipped
    )
    print(
        "Failed:",
        failed
    )
    print(
        "Folder:",
        OUTPUT_DIR
    )
    print("======================================")


if __name__ == "__main__":
    main()