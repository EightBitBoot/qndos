from typing import Dict, List

import requests
import ehp
import dateparser

ENTERPRISE_FILE_PATH = "convert_enterprise/1.3.6.1.4.1.html"

def extract_list(tag: ehp.Root) -> List[str]:
    result = []

    inner_tags = [t for t in tag if type(t) == ehp.Tag]

    for inner_tag in inner_tags:
        result.append(inner_tag.text().strip())

    
    return result


def scrape_description_list(root: ehp.Root) -> Dict:
    data = {}

    description_list = None
    try:
        description_list = list(root.find("dl"))[0]
    except IndexError as e:
        # Root doesn't contain a dl tag: Gulp
        pass

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


def main():
    ehp_parser = ehp.Html()

    # enterprise_file_contents = None
    # with open(ENTERPRISE_FILE_PATH, "rt") as enterprise_file:
    #     enterprise_file_contents = enterprise_file.read()

    # root = ehp_parser.feed(enterprise_file_contents)

    test_page_contents = None
    with open("test_page.html", "rt") as test_page_file:
        test_page_contents = test_page_file.read()

    root = ehp_parser.feed(test_page_contents)

    # response = requests.get("https://google.com")    
    # root = ehp_parser.feed(response.text)

    scraped_description_list = scrape_description_list(root)

    print(scraped_description_list)


if __name__ == "__main__":
    main()