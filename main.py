#!/usr/bin/env python3

# Requires Python 3.10 for match statement

from bs4 import BeautifulSoup
import requests
import json

BASE_URL = "https://oidref.com"
TEST_URL = "https://oidref.com/1.0.3166"

def main():
    response = requests.get(TEST_URL)
    # response = requests.get("https://oidref.com/2")
    parsed_html = BeautifulSoup(response.content, "html.parser")
    body = parsed_html.body

    data = {}

    description_list = body.find("dl")

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
            case "node_code":
                converted_desc = int(description_desc.string)
            case "node_names":
                converted_desc = [name for name in description_desc.stripped_strings]
            case "dot_oid":
                converted_desc = str(description_desc.string).strip()
            case "asn1_oid":
                converted_desc = [oid for oid in description_desc.stripped_strings]
            case "iri_oid":
                converted_desc = [iri for iri in description_desc.stripped_strings]
            case "iri_by_oid_info":
                converted_desc = [oid_info_iri for oid_info_iri in description_desc.stripped_strings]
            case "creation_date":
                #TODO(Adin): Finish this
                pass

        data[converted_term] = converted_desc

    print(json.dumps(data, indent=4))


if __name__ == "__main__":
    main()