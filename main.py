#!/usr/bin/env python3

# Requires Python 3.10 for match statement

from bs4 import BeautifulSoup
import requests
import datetime

BASE_URL = "https://oidref.com"
TEST_URL = "https://oidref.com/1.0.3166"

def scrape_description_list(soup):
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


def main():
    response = requests.get(BASE_URL + "/0")
    # response = requests.get(TEST_URL)
    soup = BeautifulSoup(response.content, "html.parser")

    data = scrape_description_list(soup)

    print(data)
    # pprint.pprint(data) 


if __name__ == "__main__":
    main()