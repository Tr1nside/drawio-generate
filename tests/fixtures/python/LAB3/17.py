def _input_data() -> tuple[float, float, float] | None:
    print("Введите длины сторон треугольника: ")
    try:
        a = float(input("a = "))
        b = float(input("b = "))
        c = float(input("c = "))
    except ValueError:
        return None

    return (a, b, c)


def _check_triangle(a: float, b: float, c: float) -> bool:
    return not (a + b <= c or a + c <= b or c + b <= a)


def _check_equilateralism(a, b, c) -> bool:
    return (a == b) and (b == c) and (c == a)


def main() -> None:
    print("Является ли треугольник со сторонами a, b, c равносторонним")
    input_data = _input_data()

    if input_data is None:
        print("Введены не числовые значения")
        return
    if _check_triangle(*input_data):
        if _check_equilateralism(*input_data):
            print("Тругольник является равносторонним")
        else:
            print("Треугольник не является равносторонним")
    else:
        print("Такого треугольника не существует")


if __name__ == "__main__":
    main()
