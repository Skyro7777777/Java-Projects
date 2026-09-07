list1 = [22, 4, 16, 38, 13]
choice = 0

while True:
    print("Current list:", list1)
    print("\nLIST OPERATIONS")
    print("1. Append")
    print("2. Insert")
    print("3. Add another list")
    print("4. Modify")
    print("5. Delete by position")
    print("6. Delete by value")
    print("7. Sort ascending")
    print("8. Sort descending")
    print("9. Display list")
    print("10. Exit")

    choice = int(input("Enter your choice (1-10): "))

    if choice == 1:
        element = int(input("Enter element: "))
        list1.append(element)
        print("Element added.\n")

    elif choice == 2:
        element = int(input("Enter element: "))
        pos = int(input("Enter position: "))
        list1.insert(pos, element)
        print("Element inserted.\n")

    elif choice == 3:
        newList = eval(input("Enter the list: "))
        list1.extend(newList)
        print("List added.\n")

    elif choice == 4:
        i = int(input("Enter position: "))
        if i < len(list1):
            newElement = int(input("Enter new element: "))
            oldElement = list1[i]
            list1[i] = newElement
            print(oldElement, "changed to", newElement, "\n")
        else:
            print("Position is not valid.")

    elif choice == 5:
        i = int(input("Enter position: "))
        if i < len(list1):
            element = list1.pop(i)
            print(element, "deleted.\n")
        else:
            print("Position is not valid.")

    elif choice == 6:
        element = int(input("Enter element to delete: "))
        if element in list1:
            list1.remove(element)
            print(element, "deleted.\n")
        else:
            print(element, "is not in the list.")

    elif choice == 7:
        list1.sort()
        print("List sorted.\n")

    elif choice == 8:
        list1.sort(reverse=True)
        print("List sorted in descending order.\n")

    elif choice == 9:
        print("List:", list1)

    elif choice == 10:
        break

    else:
        print("Invalid choice.")
        input("Press Enter to continue...")
