#!/usr/bin/env python3

import sys

def process_one(dot_oid):
    result = "DRILL_DOWN_OID = ["

    split_oid = dot_oid.split(".")

    for i in range(1, len(split_oid) + 1):
        result += f'"{".".join(split_oid[0:i])}"'

        if i != len(split_oid):
            result += ", "

    result += "]"

    return result


def main():
    in_str = " "

    if len(sys.argv) > 1:
        print(process_one(sys.argv[1]))
        return

    while True:
        in_str = input("start_oid> ").strip()

        if in_str == "" or in_str.lower() == "exit":
            return

        print(process_one(in_str), end="\n\n")


if __name__ == "__main__":
    main()
