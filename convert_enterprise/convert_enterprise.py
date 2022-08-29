import os
import time

import json
from bs4 import BeautifulSoup

ENTERPRISE_FILE_NAME = "1.3.6.1.4.1.html"
BASE_URL = "https://oidref.com"

def main():
    if not os.path.exists(ENTERPRISE_FILE_NAME):
        print("Error: Couldn't find enterprise html file!")    
        return

    soup = None
    with open(ENTERPRISE_FILE_NAME) as enterprise_file:
        then = time.perf_counter_ns()
        soup = BeautifulSoup(enterprise_file, "html.parser")
        now = time.perf_counter_ns()

        duration = now - then

        print(f"Time to Parse: {duration / 10**9}s ({duration}ns)")


    children_table = soup.find("table")
    children = []

    strings = children_table.find_all(string='\n')
    for string in strings:
        # There's gotta be a better way but idfk how
        string.extract() 

    children_table.smooth()

    first = True
    for child in children_table.children:
        if first:
            # Skip title row without enumerating
            first = False
            continue

        children.append({
            "identifier": str(child.contents[0].string),
            "link": f"{BASE_URL}/{child.contents[0].string}",
            "names": str(child.contents[1].string).split(", "),
            "sub_children": int(child.contents[2].string),
            "sub_nodes_total": int(child.contents[3].string)
        })

    with open("enterprise_compact.json", "wt+") as json_file:
        json.dump(children, json_file)

    with open("enterprise_readable.json", "wt+") as hjson_file:
        json.dump(children, hjson_file, indent=4)


if __name__ == "__main__":
    main()