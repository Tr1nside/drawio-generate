x = float(input("Введите действительное число x: "))

i = 2
total_up = x - i
while i < 65:
    i *= 2
    total_up *= x - i


i = 2
total_down = x - (i - 1)
while i < 65:
    i *= 2
    total_down *= x - (i - 1)

result = total_up / total_down
print(f"Результат: {result}")
