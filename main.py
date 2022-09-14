#!/usr/bin/env python3

# Requires Python 3.10 for match statement

from typing import Dict

import datetime
import re
from collections import namedtuple
import json
import os
import concurrent.futures
from math import floor
import time
import pprint
import sys

import bs4 # Needed for bs4.element.Tag type in get_next_sibling_tag
from bs4 import BeautifulSoup
import requests
from markdownify import markdownify
from pymongo import MongoClient
import dateparser

BASE_URL = "https://oidref.com"
ZERO_URL = "https://oidref.com/0"
ONE_URL = "https://oidref.com/1"
TWO_URL = "https://oidref.com/2"

# Testing URLs
GENERAL_TEST_URL = "https://oidref.com/1.0.3166"
DETAILS_STRESS_TEST_URL = "https://oidref.com/1.0.8802.1.1.2.0.0.1"
NO_CHILDREN_URL = "https://oidref.com/0.5"

# Child object for child scraper
Child = namedtuple("Child", ["url", "direct_children", "subnodes_total"])

# Globals
MULTITHREAD_LIST = []
SKIP_URLS = ["https://oidref.com/1.3.6.1.4.1"]

mongodb_client = None

current_root_node = None # Used for exception logging

# ------------------ Utils ------------------

def get_next_sibling_tag(tag):
    while tag.next_sibling and type(tag.next_sibling) != bs4.element.Tag:
        tag = tag.next_sibling

    return tag.next_sibling


# ------------------ Scrapers ------------------

def scrape_description_list(soup: BeautifulSoup) -> Dict:
    data = {}

    description_list = soup.find("dl")

    if description_list == None:
        return None

    for description_term in description_list.find_all("dt"):
        converted_term = str(description_term.string).lower().replace(" ", "_")
        description_desc = description_term.next_sibling
        
        if converted_term == "node_name":
            # Standardize differences in webpage dt naming
            converted_term = "node_names"

        converted_desc = None
        match converted_term:
            case "parent":
                if not description_desc.a:
                    continue

                converted_desc = str(description_desc.a.string).strip()
                if converted_desc == "None":
                    # Special case for root nodes
                    converted_desc = None
            case "node_code":
                try:
                    converted_desc = int(description_desc.string)
                except:
                    if str(description_desc.string).strip() == "None":
                        converted_desc = None
                    else:
                        converted_desc = str(description_desc.string).strip()
            case "node_names" | "asn1_oid" | "iri_oid":
                converted_desc = [str(name) for name in description_desc.stripped_strings]
            case "creation_date" | "modification_date":
                # {"TIMEZONE": "UTC"} avoids a PytzUsageWarning
                converted_desc = dateparser.parse(str(description_desc.string), settings={"TIMEZONE": "UTC"})
            case _:
                converted_desc = str(description_desc.string).strip()

        data[converted_term] = converted_desc

    return data


def scrape_detailed_data(soup: BeautifulSoup) -> Dict:
    data = {}

    headers = soup.find_all("h3")

    for header in headers:
        converted_header = (" ".join(list(header.stripped_strings))).lower().replace(" ", "_")
        next_sibling_tag = get_next_sibling_tag(header)

        if not next_sibling_tag:
            continue

        if "recovered" in converted_header:
            # Ignore "recovered" sections
            continue

        if "registration_authority" in converted_header:
            # Handle unclosed paragraph tags
            html_str = str(next_sibling_tag)
            split_str = html_str.split("<h3>")
            data[converted_header] = markdownify(split_str[0].strip()).strip()
            continue

        if next_sibling_tag.name != "p" and next_sibling_tag.name != "pre":
            # Handle headers for Children and Brothers tables
            break

        data[converted_header] = markdownify(str(next_sibling_tag)).strip()

    return data


def scrape_children(soup):
    children = []

    children_header = soup.find(name="h3", string=re.compile("[cC]hildren"))

    if not children_header:
        return children

    children_table = get_next_sibling_tag(children_header)

    if not children_table:
        return children

    first = True
    for table_row in children_table.find_all("tr"):
        if first:
            # Skip first without enumerating
            first = False
            continue

        table_cells = table_row.find_all("td")
        children.append(Child(
            url=f"{BASE_URL}/{table_cells[0].a.string}",
            direct_children=int(table_cells[2].string),
            subnodes_total=int(table_cells[3].string)
        ))

    return children


# ------------------ Traverser ------------------

def traverse_tree(url: str):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    data = {"scrape_time": time.time_ns()}
    scraped_dl = scrape_description_list(soup)

    if scraped_dl == None:
        with open("no_dl_page.html", "w+t") as error_file:
            error_file.write(soup.prettify())

        print(f"Page for {url.split('/')[-1]} didn't contain a dl: exiting!")
        print(f"Root node: {current_root_node}") # Added for resuming scraping of the children of enterprise
        exit(1)

    data.update(scraped_dl)
    data["detailed_data"] = scrape_detailed_data(soup)

    mongodb_collection = mongodb_client.qndos.oids
    if mongodb_collection.find_one({"dot_oid": data["dot_oid"]}):
        print(f"Warning: oid {data['dot_oid']} is already in the database. Skipping", flush=True)
    else:
        mongodb_collection.insert_one(data)
        print(data["dot_oid"], flush=True)

    children = scrape_children(soup)
    
    if data["dot_oid"] in MULTITHREAD_LIST:
        print(f"Multithreading on children of {data['dot_oid']}", flush=True)
        process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=floor(3 / 4 * os.cpu_count()))
        futures = []
        for child in children:
            if child.url in SKIP_URLS:
                continue
            futures.append(process_pool.submit(entrypoint, child.url))

        concurrent.futures.wait(futures)
    else:
        for child in children:
            if child.url in SKIP_URLS:
                continue
            traverse_tree(child.url)
    

def grab_enterprise_children():
    enterprise_file_path = "convert_enterprise/enterprise_compact.json"
    if not os.path.exists(enterprise_file_path):
        print(f"Converted enterprise children file not found at \"{enterprise_file_path}\"!")
        exit(1)

    enterprise_children_list = None
    with open(enterprise_file_path, "rt") as enterprise_file:
        enterprise_children_list = json.load(enterprise_file)

    return enterprise_children_list


def new_except_hook(exception_type, value, backtrace):
    global old_excepthook

    print(f"------------- Exception under root node {current_root_node} -------------")
    sys.__excepthook__(exception_type, value, backtrace)


def entrypoint(url: str):
    global mongodb_client
    global current_root_node

    mongodb_client = None

    if not os.path.exists("secrets.json"):
        print("secrets.json file not found! Create a json file with four keys: mongo_database, mongo_username, mongo_database, mongo_passwd")

    with open("secrets.json", "rt") as secrets_file:
        secrets = json.load(secrets_file)    
        mongodb_client = MongoClient(
            secrets["mongo_url"],
            username=secrets["mongo_username"],
            password=secrets["mongo_passwd"],
            authSource=secrets["mongo_database"],
            authMechanism="SCRAM-SHA-1"
        )

    sys.excepthook = new_except_hook 

    enterprise_children_list = grab_enterprise_children()
    
    for child in enterprise_children_list:
        current_root_node = child["link"].split("/")[-1]
        
        traverse_tree(child["link"])

def main():
    local_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    run_date = datetime.datetime.now(local_timezone)

    # Avoid max recursion crashes
    sys.setrecursionlimit(10**6)

    if not os.path.exists("runtimes"):
        os.mkdir("runtimes")

    runtime_file_url = f"runtimes/{run_date.strftime('%Y.%m.%d_%H:%M:%S')}_runtime.txt"

    then = time.time_ns()

    with open(runtime_file_url, "w+t") as runtime_file:
        runtime_file.write(f"Start: {str(then)}\n")

    entrypoint(ONE_URL)

    now = time.time_ns()

    with open(runtime_file_url, "a+t") as time_file:
        time_file.write(f"End: {str(now)}\n")
        time_file.write(f"Runtime: {str(now - then)}\n")


if __name__ == "__main__":
    main()
