#!/usr/bin/env python3

# Requires Python 3.10 for match statement

from typing import Dict

import bs4 # Needed for bs4.element.Tag type in get_next_sibling_tag
from bs4 import BeautifulSoup
import requests
import datetime
from markdownify import markdownify

BASE_URL = "https://oidref.com"
TEST_URL = "https://oidref.com/1.0.3166"

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

        if "registration_authority" in converted_header:
            # TODO(Adin): !BEFORE INSERTING INTO DATABASE! Figure out what to do with unclosed registration authority paragraph tags
            continue

        if next_sibling_tag.name != "p":
            # Handle headers for Children and Brothers tables
            break

        data[converted_header] = markdownify(str(next_sibling_tag)).strip()

    return data


def test(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    data = scrape_description_list(soup)
    detailed_data = scrape_detailed_data(soup)
    data["detailed_data"] = detailed_data
    print(url)
    print(data)


def main():
    test(BASE_URL + "/0")
    print("\n--------------------\n")
    test(TEST_URL)


if __name__ == "__main__":
    main()