#Menu driven program to do various list operations
list1 = [22,4,16,38,13] #list1 has 5 elements
choice = 0
while True:
    print("The list has the following elements", list1)
    print("\n L I S T   O P E R A T I O N S")
    print(" 1. Append an element")
    print(" 2. Insert an element at the desired position")
    print(" 3. Append a list to the given list")
    print(" 4. Modify an existing element")
    print(" 5. Delete an existing element by its position")
    print(" 6. Delete an existing element by its value")
    print(" 7. Sort the list in ascending order")
    print(" 8. Sort the list in descending order")
    print(" 9. Display the list")
    print(" 10. Exit")
    choice = int(input("ENTER YOUR CHOICE (1-10): "))
    #append element
    if choice == 1:
        element = int(input("Enter the element to be appended: "))
        list1.append(element)
        print("The element has been appended\n")
    #insert an element at desired position
    elif choice == 2:
        element = int(input("Enter the element to be inserted: "))
        pos = int(input("Enter the position:"))
        list1.insert(pos,element)
        print("The element has been inserted\n")
    #append a list to the given list
    elif choice == 3:
        newList = eval(input("Enter the list to be appended: "))
        list1.extend(newList)
        print("The list has been appended\n")
    #modify an existing element
    elif choice == 4:
        i = int(input("Enter the position of the element to be modified: "))
        if i < len(list1):
            newElement = int(input("Enter the new element: "))
            oldElement = list1[i]
            list1[i] = newElement
            print("The element",oldElement,"has been modified\n")
        else:
            print("Position of the element is more than the length of list")
    #delete an existing element by position
    elif choice == 5:
        i = int(input("Enter the position of the element to be deleted: "))
        if i < len(list1):
            element = list1.pop(i)
            print("The element",element,"has been deleted\n")
        else:
            print("\nPosition of the element is more than the length of list")
    #delete an existing element by value
    elif choice == 6:
        element = int(input("\nEnter the element to be deleted: "))
        if element in list1:
            list1.remove(element)
            print("\nThe element",element,"has been deleted\n")
        else:
            print("\nElement",element,"is not present in the list")
    #list in sorted order
    elif choice == 7:
        list1.sort()
        print("\nThe list has been sorted")
    #list in reverse sorted order
    elif choice == 8:
        list1.sort(reverse = True)
        print("\nThe list has been sorted in reverse order")
    #display the list
    elif choice == 9:
        print("\nThe list is:", list1)
    #exit from the menu
    elif choice == 10:
        break
    else:
        print("Choice is not valid")
        print("\n\nPress any key to continue...........")
        ch = input()
