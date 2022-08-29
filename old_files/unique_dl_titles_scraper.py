#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import time
import os
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import math

BASE_URL = "https://oidref.com"

TOP_LEVEL_URLS = [
    "https://oidref.com/0",
    "https://oidref.com/1",
    "https://oidref.com/2"
]

TERMS_DIR = "terms"

MAX_PAGES = 100
num_pages = 0


def scrape_data(soup, current_term_set):
    body = soup.body

    dot_oid = body.find("h1").string.split()[-1]
    # print(dot_oid, end=",")

    description_list = body.find("dl")

    for description_term in description_list.find_all("dt"):
        converted_term = str(description_term.string).lower().replace(" ", "_")
        
        if converted_term == "node_name":
            # Standardize differences in webpage dt naming
            converted_term = "node_names"

        if converted_term not in current_term_set:
            with open(f"{TERMS_DIR}/{os.getpid()}_terms.txt", "at+") as term_file:
                term_file.write(f"{converted_term}: {dot_oid}\n")

            current_term_set.add(converted_term)


def traverse_tree(url, depth, current_term_set):
    global num_pages

    # if num_pages >= 100:
    #     return set()

    if depth > 6:
        print(f"Depth: {depth}")
        return set()

    # if num_pages != 0 and num_pages % 32 == 0:
    #     print()
    # print(".", end="", flush=True)

    if not os.path.exists(TERMS_DIR):
        os.mkdir(TERMS_DIR)

    num_pages += 1

    response = requests.get(url)

    soup = BeautifulSoup(response.content, "html.parser")

    scrape_data(soup, current_term_set)

    executor = None 
    if depth == 2:
        executor = ProcessPoolExecutor(max_workers=math.floor(mp.cpu_count() * 3 / 4))
        pass

    body = soup.body
    children_header = body.find(lambda tag: tag.name == "h3" and tag.string and "Children" in tag.string)
    if children_header:
        children_table = children_header.next_sibling.next_sibling
        futures = []
        for table_row in children_table.find_all("tr"):
            if table_entry := table_row.find("td"):
                child_url = f"{BASE_URL}/{table_entry.a.string.strip()}"
                print(table_entry.a.string.strip())
                if executor:
                    futures.append(executor.submit(traverse_tree, child_url, depth + 1, current_term_set))
                else:
                    current_term_set |= traverse_tree(child_url, depth + 1, current_term_set)

        if executor:
            for future in concurrent.futures.as_completed(futures):
                current_term_set |= future.result()

    return current_term_set


def main():
    term_set = set()

    for url in TOP_LEVEL_URLS:
        term_set |= traverse_tree(url, 1, term_set)

    print("\n", term_set, sep="")


if __name__ == "__main__":
    main()