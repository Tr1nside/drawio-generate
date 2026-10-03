"""Генератор блок-схем drawio из исходного кода (Python / C#).

Пакет разделён на слои:

* :mod:`drawio_gen.ir` — язык-нейтральное промежуточное представление;
* :mod:`drawio_gen.parsers` — разбор языков в IR;
* :mod:`drawio_gen.optimizer` — оптимизация IR;
* :mod:`drawio_gen.layout` — укладка IR в геометрию;
* :mod:`drawio_gen.render` — сериализация в ``.drawio`` и SVG;
* :mod:`drawio_gen.web` — Flask-приложение.
"""

__all__ = ["__version__"]

__version__ = "0.3.0"
