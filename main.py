#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests

BASE_URL = "https://oidref.com"

def main():
    response = requests.get(BASE_URL)
    parsed_html = BeautifulSoup(response.content, "html.parser")

    print(parsed_html.prettify())


if __name__ == "__main__":
    main()