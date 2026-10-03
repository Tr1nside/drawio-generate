s = input("Введите строку: ")

result = ""
for i in range(0, len(s), 3):
    chunk = s[i : i + 3]
    result += chunk
    if len(chunk) == 3:
        result += " "

print(f"Новая строка: '{result}'")


