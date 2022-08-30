#!/usr/bin/env python3

# Requires Python 3.10 for match statement

from typing import Dict

import datetime
import pprint
import re
from collections import namedtuple

import bs4 # Needed for bs4.element.Tag type in get_next_sibling_tag
from bs4 import BeautifulSoup
import requests
from markdownify import markdownify

BASE_URL = "https://oidref.com"

# Testing URLs
ZERO_URL = "https://oidref.com/0"
GENERAL_TEST_URL = "https://oidref.com/1.0.3166"
DETAILS_STRESS_TEST_URL = "https://oidref.com/1.0.8802.1.1.2.0.0.1"
NO_CHILDREN_URL = "https://oidref.com/0.5"

# Child object for child scraper
Child = namedtuple("Child", ["url", "direct_children", "subnodes_total"])

# ------------------ Utils ------------------

def get_next_sibling_tag(tag):
    while tag.next_sibling and type(tag.next_sibling) != bs4.element.Tag:
        tag = tag.next_sibling

    return tag.next_sibling


# ------------------ Scrapers ------------------

def scrape_description_list(soup: BeautifulSoup) -> Dict:
    data = {}

    description_list = soup.find("dl")

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
                converted_desc = int(description_desc.string)
            case "node_names" | "asn1_oid" | "iri_oid":
                converted_desc = [str(name) for name in description_desc.stripped_strings]
            case "creation_date" | "modification_date":
                converted_desc = datetime.datetime.strptime(str(description_desc.string).strip(), "%b. %d, %Y")
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

MULTITHREAD_LIST = []

MAX_NODES = 100
num_nodes = 0

def traverse_tree(url):
    global num_nodes

    if num_nodes >= MAX_NODES:
        return

    num_nodes += 1

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    data = scrape_description_list(soup)
    data["detailed_data"] = scrape_detailed_data(soup)

    print(data["dot_oid"])
    # TODO(Adin): Store in mongodb here

    children = scrape_children(soup)
    
    if data["dot_oid"] in MULTITHREAD_LIST:
        # TODO(Adin): Use multiprocessing here
        pass
    else:
        for child in children:
            traverse_tree(child.url)
    

def test(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    print("\n".join([str(x) for x in scrape_children(soup)]))
    return

    data = scrape_description_list(soup)
    detailed_data = scrape_detailed_data(soup)
    data["detailed_data"] = detailed_data
    print(url)
    pprint.pprint(data, sort_dicts=False)


def main():
    # test(DETAILS_STRESS_TEST_URL)

    # test(ZERO_URL)
    # print("\n--------------------\n")
    # test(GENERAL_TEST_URL)
    # print("\n--------------------\n")
    # test(NO_CHILDREN_URL)

    traverse_tree(ZERO_URL)


if __name__ == "__main__":
    main()