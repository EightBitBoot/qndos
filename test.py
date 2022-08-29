#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import time

BASE_URL = "https://oidref.com"

TOP_LEVEL_URLS = [
    "https://oidref.com/0",
    "https://oidref.com/1",
    "https://oidref.com/2"
]

term_set = set()

def scrape_data(soup):
    body = soup.body

    dot_oid = body.find("h1").string.split()[-1]
    print(dot_oid, end=",")

    description_list = body.find("dl")

    for description_term in description_list.find_all("dt"):
        converted_term = str(description_term.string).lower().replace(" ", "_")
        
        if converted_term == "node_name":
            # Standardize differences in webpage dt naming
            converted_term = "node_names"

        if converted_term not in term_set:
            with open("terms.txt", "at+") as term_file:
                term_file.write(f"{converted_term}: {dot_oid}\n")

            term_set.add(converted_term)


MAX_PAGES = 100
num_pages = 0


def traverse_tree(url):
    global num_pages

    if num_pages >= 100:
        return

    num_pages += 1

    then_response = time.perf_counter_ns()
    response = requests.get(url)
    now_response = time.perf_counter_ns()

    then_soup = time.perf_counter_ns()
    soup = BeautifulSoup(response.content, "html.parser")
    now_soup = time.perf_counter_ns()

    scrape_data(soup)
    print(f"{now_response - then_response},{now_soup - then_soup}")

    body = soup.body
    children_header = body.find(lambda tag: tag.name == "h3" and tag.string and "Children" in tag.string)
    if children_header:
        children_table = children_header.next_sibling.next_sibling
        for table_row in children_table.find_all("tr"):
            if table_entry := table_row.find("td"):
                traverse_tree(f"{BASE_URL}/{table_entry.a.string.strip()}")


def main():
    for url in TOP_LEVEL_URLS:
        traverse_tree(url)

    print(term_set)


def lambda_handler(event, context):
    main()

    return "Fuck off m8"