from typing import Dict, List, Tuple

import re
import json
import time
import copy
from collections import namedtuple

import requests
import ehp
import dateparser
from markdownify import markdownify

ENTERPRISE_FILE_PATH = "convert_enterprise/1.3.6.1.4.1.html"

BASE_URL = "https://oidref.com"

Child = namedtuple("Child", ["url", "direct_children", "subnodes_total"])

def extract_list(tag: ehp.Root) -> List[str]:
    result = []

    inner_tags = [t for t in tag if type(t) == ehp.Tag]

    for inner_tag in inner_tags:
        result.append(inner_tag.text().strip())

    
    return result


def scrape_description_list(root: ehp.Root) -> Dict:
    data = {}

    description_list = root.fst("dt")

    if description_list == None:
        # Skip scraping if Root doesn't contain a dl tag
        return None

    section_titles = [dt.text().strip().lower().replace(" ", "_") for dt in description_list.find("dt")]   
    section_contents = list(description_list.find("dd"))

    for i in range(len(section_titles)):
        section_title = section_titles[i]
        section_content = section_contents[i]
        
        if section_title == "node_name":
            # Standardize differences in webpage dt naming
            section_title = "node_names"

        converted_content = None
        match section_title:
            case "parent":
                anchor = section_content.fst("a")                

                if not anchor:
                    continue

                converted_content = anchor.text().strip()
                if converted_content == "None":
                    # Special case for root nodes
                    converted_content = None
            case "node_code":
                try:
                    converted_content = int(section_content.text())
                except:
                    if section_content.text().strip() == "None":
                        converted_content = None
                    else:
                        converted_content = section_content.text().strip()
            case "node_names":
                if len(section_content) == 1:
                    converted_content = [section_content.text().strip()]
                else:
                    converted_content = extract_list(section_content)
            case "asn1_oid" | "iri_oid":
                converted_content = extract_list(section_content)
            case "creation_date" | "modification_date":
                # {"TIMEZONE": "UTC"} avoids a PytzUsageWarning
                converted_content = dateparser.parse(section_content.text(), settings={"TIMEZONE": "UTC"})
            case _:
                converted_content = section_content.text().strip()

        data[section_title] = converted_content

    return data


PARAGRAPH_SPLIT_PATTERN = re.compile(r"\<\s*h3\s*\>")    

def scrape_detailed_data(root: ehp.Root) -> Dict:
    data = {}

    def get_pairs():
        result = []

        for parent,header in root.find_with_root("h3"):
            header_index = parent.index(header)

            paragraph_index = header_index + 1
            while type(parent[paragraph_index]) != ehp.Tag and paragraph_index < len(parent):
                # Skip non Tag items in parent
                paragraph_index += 1

            if paragraph_index >= len(parent):
                continue

            result.append((header, parent[paragraph_index]))

        return result


    def get_authority_paragraph(root: ehp.Tag) -> Tuple[ehp.Tag, bool]:
        # TODO(Adin): This needs to be cleaned up or rewritten

        result = ehp.Tag(name=root.name, attr=root.attr)

        for child in root:
            if type(child) in [ehp.Data, ehp.Amp, ehp.Code, ehp.XTag]:
                result.append(child)
                continue

            if child.name == "h3":
                return (result,True)

            new_child,h3_found = get_authority_paragraph(child)
            result.append(new_child)

            if h3_found:
                return (result,True)


        return (result,False)


    header_paragraph_pairs = get_pairs()

    for header,paragraph in header_paragraph_pairs:
        converted_header = header.text().strip().lower().replace(" ", "_")

        if "recovered" in converted_header:
            # Ignore "recovered" sections
            continue

        if "registration_authority" in converted_header:
            truncated_paragraph,_ = get_authority_paragraph(paragraph)
            data[converted_header] = markdownify(str(truncated_paragraph)).strip()
            continue

        if "children" in converted_header or "brothers" in converted_header:
            break

        data[converted_header] = markdownify(str(paragraph)).strip()

    return data


def scrape_children(root: ehp.Root):
    def get_children_table():
        children_header_root = None
        children_header = None

        for header_root,header in root.find_with_root("h3"):
            if re.search(r"[cC]hildren", header.text().strip()):
                children_header_root,children_header = header_root,header
                break

        if not children_header:
            return children

        children_table_index = children_header_root.index(children_header) + 1
        while children_table_index <= len(children_header_root) and type(children_header_root[children_table_index]) != ehp.Tag:
            children_table_index += 1

        if children_table_index >= len(children_header_root):
            return None

        return children_header_root[children_table_index]


    children = []

    children_table = get_children_table()

    if not children_table:
        return children

    first = True
    for table_row in children_table.find("tr"):
        if first:
            # Skip first without enumerating
            first = False
            continue

        table_cells = list(table_row.find("td"))
        children.append(Child(
            url=f"{BASE_URL}/{table_cells[0].text().strip()}",
            direct_children=int(table_cells[2].text().strip()),
            subnodes_total=int(table_cells[3].text().strip())
        ))

    return children


def main():
    ehp_parser = ehp.Html()

    # Enterprise File
    enterprise_file_contents = None
    with open(ENTERPRISE_FILE_PATH, "rt") as enterprise_file:
        enterprise_file_contents = enterprise_file.read()

    then = time.perf_counter()
    root = ehp_parser.feed(enterprise_file_contents)

    # Test Page
    # test_page_contents = None
    # with open("test_page.html", "rt") as test_page_file:
    #     test_page_contents = test_page_file.read()

    # then = time.perf_counter()
    # root = ehp_parser.feed(test_page_contents)

    # No dl
    # response = requests.get("https://google.com")    

    # then = time.perf_counter()
    # root = ehp_parser.feed(response.text)

    # No Children With Brothers
    # response = requests.get("https://oidref.com/1.3.6.1.4.1.24")

    # then = time.perf_counter()
    # root = ehp_parser.feed(response.text)

    scraped_description_list = scrape_description_list(root)
    # print(scraped_description_list)

    scraped_detailed_data = scrape_detailed_data(root)
    # print(json.dumps(scraped_detailed_data, indent=4))

    children = scrape_children(root)
    print("\n".join([str(c) for c in children]))

    print()

    print(len(children))

    now = time.perf_counter()

    print(now - then)


if __name__ == "__main__":
    main()