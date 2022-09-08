
def main():
    in_str = " "

    while True:
        in_str = input("start_oid> ").strip()

        if in_str == "" or in_str.lower() == "exit":
            return

        split_str = in_str.split(".")

        print("DRILL_DOWN_OID = [", end="")
        for i in range(1, len(split_str) + 1):
            print(f'"{".".join(split_str[0:i])}"', end="")

            if i != len(split_str):
                print(", ", end="")

        print("]\n\n", end="")


if __name__ == "__main__":
    main()
