# PythonNginx

Учебный упрощенный аналог nginx на Python: асинхронный HTTP-сервер со статикой,
keep-alive, virtual hosts, autoindex, open file cache, логированием, proxy_pass,
простым распределением нагрузки между upstream и HTTPS.

Главный документ по архитектуре и плану реализации: [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md).

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pynginx --config config/pynginx.conf
```

Без установки:

```bash
PYTHONPATH=src python3 -m pynginx --config config/pynginx.conf
```

Тесты:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Дополнительные материалы:

- [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) - архитектура и проверка.
- [docs/NON_OBVIOUS.md](docs/NON_OBVIOUS.md) - неочевидные решения и зачем они нужны.
- [docs/PYTHON_HTTP_CHEATSHEET.md](docs/PYTHON_HTTP_CHEATSHEET.md) - краткая шпаргалка по использованным функциям и конструкциям.
