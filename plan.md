# Генератор блок-схем из кода (drawio)

Веб-приложение: пользователь вставляет код на **Python** или **C#**, на выходе
получает файл `.drawio` с блок-схемой. Один файл содержит несколько страниц
(diagram): `main` и по одной на каждую функцию/метод.

## Стек

- **Бэкенд:** Flask; Python — стандартный `ast`; C# — `tree-sitter`
  (пакет `tree-sitter-language-pack`). Парсеры скрыты за общим интерфейсом
  `parsers.LanguageParser` (см. раздел «Поддержка C#»).
- **Фронтенд:** чистые HTML/CSS/JS, без сборки и тяжёлых зависимостей.
- Зависимости: `flask`, `tree-sitter-language-pack`.

## Сопоставление конструкций Python → фигуры drawio

| Python                          | Фигура drawio                          | Стиль                          |
|---------------------------------|----------------------------------------|--------------------------------|
| Начало / Конец                   | **Terminator** (единственный на страницу) | `rounded=1;arcSize=50`      |
| Начало функции                   | Terminator с текстом `Начало <имя>`    | `rounded=1;arcSize=50`         |
| `x = ...`, `x += ...`            | Process (прямоугольник)                | `rounded=0`                    |
| `input(...)`                     | Параллелограмм (ввод)                  | `shape=parallelogram`          |
| `print(...)`                     | Параллелограмм (вывод)                 | `shape=parallelogram`          |
| `if / elif / else`               | Ромб (условие)                         | `rhombus`                      |
| `while`                          | Ромб (условие) + обратная дуга         | `rhombus`                      |
| `for`                            | **Шестиугольник**                      | `shape=hexagon`                |
| `def`                            | отдельная страница; вызов — Process    | —                              |
| `return`                         | дуга к единственному узлу «Конец»      | —                              |
| не распознано (try/class/with/…) | блок **«прочее»** с исходным кодом     | `rounded=0`                    |

## Архитектура

```
drawio-gen/
  app.py            # Flask: GET "/" , POST "/convert" -> XML
  parser.py         # ast -> IR
  ir.py             # dataclass-узлы IR
  layout.py         # IR -> координаты
  drawio.py         # координаты -> mxGraph XML
  requirements.txt  # flask
  templates/index.html
  static/app.js
  static/style.css
```

Пайплайн: `ast.parse` → IR → layout (x/y) → XML → ответ фронтенду → скачивание `.drawio`.

### IR (промежуточное представление)

Узлы-датаклассы: `Sequence`, `Assign`, `Input`, `Output`, `If`, `While`, `For`,
`FuncCall`, `Return`, `Other`. Линейные инструкции объединяются в `Sequence`,
ветвления и циклы — вложенные узлы.

### Парсер (`parser.py`)

- Разбор через `ast.parse`, обход `ast.walk`/рекурсия по телу.
- Каждая `def` разбирается отдельно и становится отдельной страницей.
- На главной странице `def` не рисуется, только вызовы функций (Process-блок).
- Для неподдерживаемых конструкций — `ast.get_source_segment` → узел `Other`.

### Укладка (`layout.py`)

- Рекурсивный расчёт bbox поддерева.
- Последовательность — вертикально; `if/else` — ветки влево/вправо;
  цикл — тело вниз + обратная дуга.
- Исключение наложений за счёт учёта габаритов поддеревьев.

### Генерация XML (`drawio.py`)

- Фигуры: terminator, process (прямоугольник), параллелограмм, ромб, шестиугольник.
- Рёбра: `edgeStyle=orthogonalEdgeStyle`.
- Экранирование XML и переносов строк; детерминированные id ячеек.
- Несколько страниц: `<mxfile><diagram name="main">…<diagram name="func">…`.

## Правила, обязательные к соблюдению

- Начало и конец диаграммы — в единственном экземпляре, фигура Terminator.
- Ввод и вывод — параллелограмм.
- Условие (в т.ч. `while`) — ромб.
- `for` — шестиугольник.
- Неподдерживаемое — блок «прочее».

## Этапы работ

1. Каркас Flask, страница с textarea + кнопка «Скачать .drawio».
2. `ir.py` + `parser.py`: assign/input/print/if/elif/else/while/for → IR.
3. `drawio.py`: генерация XML с нужными фигурами.
4. `layout.py`: вертикальная укладка, ветки if/else, обратные дуги циклов.
5. Функции: по странице на `def`, старт `Начало <имя>`, вызовы как Process.
6. `return` → дуги в единственный «Конец»; неподдерживаемое → блок «прочее».
7. Проверка на `LAB3/17.py`, `LAB4/22.py`, `LAB5/66.py`.

## Критерии готовности

- Сгенерированные `.drawio` открываются в app.diagrams.net.
- Ровно один Terminator начала и один конца на каждой странице.
- Фигуры соответствуют таблице сопоставления.
- Код с функциями даёт отдельную страницу на каждую функцию.

## Поддержка C#

### Архитектура (SOLID)

- `parsers/base.py` — интерфейс `LanguageParser` и ошибка `ParseError`.
- `parsers/python_parser.py`, `parsers/csharp_parser.py` — реализации.
- `parsers/registry.py` — реестр; `app.py` зависит от абстракции (DIP).
- Добавление языка не требует правок в `layout/drawio/preview` (OCP).

### Сопоставление C# → IR

| C#                                   | IR                                       |
|--------------------------------------|------------------------------------------|
| `namespace`/`class`/`using`/атрибуты | пропускаются, обход вложенных методов    |
| метод                                | `Page`; `Main` → страница `main`          |
| `Console.ReadLine`/`Read`            | `Input`                                  |
| `Console.WriteLine`/`Write`          | `Output`                                 |
| `if / else if / else`                | `If` (цепочка через `else_body`)          |
| `switch/case/default`                | цепочка `If` (`x == value`)               |
| `while` / `do-while`                 | `While` (ромб)                            |
| `for` / `foreach`                    | `For` (шестиугольник)                     |
| `return`/`break`/`continue`          | `Return`/`Break`/`Continue`               |
| `try/catch/finally`                  | тело + `Other` для catch/finally          |
| `throw`                              | `Other`                                   |
| прочее                               | `Other`                                   |

### Автодетект и интерфейс

- `LanguageRegistry.detect` выбирает язык по эвристикам (fallback — Python).
- В UI — селектор «Авто / Python / C#», выбор хранится в `localStorage`.
