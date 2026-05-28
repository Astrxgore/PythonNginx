# PythonNginx: как устроен проект

Это учебный упрощенный аналог nginx. Он не пытается повторить весь nginx, но закрывает главные требования задачи:

- асинхронная обработка TCP-соединений через `asyncio`;
- ручной разбор HTTP/1.0 и HTTP/1.1;
- keep-alive;
- отдача статических файлов;
- autoindex для каталогов;
- open file cache с кэшем открытых файловых дескрипторов;
- access log;
- virtual servers по заголовку `Host`;
- конфигурация через файл;
- `proxy_pass` на HTTP upstream.
- распределение нагрузки между несколькими upstream с failover;
- HTTPS через стандартный модуль `ssl`.

## Как запустить

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pynginx --config config/pynginx.conf
```

Без установки пакета можно запускать так:

```bash
PYTHONPATH=src python3 -m pynginx --config config/pynginx.conf
```

Тесты:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Общая схема

Путь одного запроса:

1. `__main__.py` читает аргументы командной строки.
2. `config/loader.py` читает `config/pynginx.conf`.
3. `server/app.py` запускает `asyncio.start_server`.
4. На каждое TCP-соединение вызывается `server/connection.py`.
5. `http/parser.py` читает байты до `\r\n\r\n` и вручную разбирает HTTP-заголовки.
6. `server/router.py` выбирает virtual server и location.
7. Если у location есть `proxy_pass`, запрос уходит в `proxy/upstream.py`.
8. Иначе запрос обслуживает `static/files.py`.
9. Ответ собирается в `http/response.py`.
10. `logging.py` пишет access log.
11. Если keep-alive разрешен, соединение остается открытым и цикл ждет следующий запрос.

## Файловая структура

```text
src/pynginx/
  __main__.py              # входная точка
  config/
    loader.py              # чтение ini-конфига
    models.py              # dataclass-модели конфигурации
  http/
    parser.py              # ручной HTTP parser
    request.py             # модель HTTPRequest
    response.py            # модель HTTPResponse
  server/
    app.py                 # запуск listen-сокетов
    connection.py          # цикл одного TCP-соединения и keep-alive
    router.py              # virtual hosts и location matching
  static/
    files.py               # отдача файлов и защита от path traversal
    open_file_cache.py     # LRU-кэш открытых fd
    autoindex.py           # HTML-индекс каталога
  proxy/
    upstream.py            # простой reverse proxy
  logging.py               # access log
```

## Конфигурация

Пример находится в `config/pynginx.conf`.

```ini
[main]
header_limit = 16384
body_limit = 2097152
keepalive_timeout = 30
keepalive_max_requests = 100
open_file_cache_max = 128
open_file_cache_inactive = 30
proxy_timeout = 10

[server:local]
listen = 127.0.0.1:8080
server_name = localhost 127.0.0.1
root = public
autoindex = on
access_log = logs/access.log

[location:local:/]
root = public
autoindex = on

[location:local:/api/]
proxy_pass = http://127.0.0.1:9000 http://127.0.0.1:9001

[server:secure]
listen = 0.0.0.0:8443
server_name = secure.local
root = public
autoindex = on
ssl = on
ssl_certfile = certs/server.crt
ssl_keyfile = certs/server.key
```

`[main]` задает общие лимиты.

`[server:name]` описывает virtual server: где слушать, какие имена хоста принимать, где лежит статика. Если указать `ssl = on`, сервер слушает HTTPS и загружает сертификат из `ssl_certfile` и ключ из `ssl_keyfile`.

`[location:server_name:/prefix/]` задает правило для URL-префикса. Если есть `proxy_pass`, запрос проксируется. Если в `proxy_pass` перечислено несколько URL через пробел, они используются как upstream-пул. Если нет `proxy_pass`, отдается статика.

## HTTP parser

HTTP поверх TCP приходит как поток байтов. TCP не говорит серверу: "вот один запрос". Поэтому сервер ищет границу HTTP-заголовков сам.

В `http/parser.py` используется:

```python
reader.readuntil(b"\r\n\r\n")
```

Это читает только request line и headers. Для обычного `GET` больше ничего читать не надо.

Парсер вручную:

- разбирает первую строку на `method`, `target`, `version`;
- проверяет `HTTP/1.0` или `HTTP/1.1`;
- складывает headers в словарь;
- приводит имена headers к lower-case;
- проверяет обязательный `Host` для HTTP/1.1;
- поддерживает тело только через `Content-Length`;
- отклоняет chunked request body как `501 Not Implemented`.

Тело читается отдельной функцией `read_body()`. Это важно: для статики тело обычно не нужно, а для proxy оно может понадобиться.

## Keep-alive

Keep-alive реализован в `server/connection.py`.

Идея простая: одно TCP-соединение обслуживается циклом:

```text
прочитать запрос -> отправить ответ -> решить, закрывать или ждать следующий
```

Правила:

- HTTP/1.1 по умолчанию держит соединение открытым;
- `Connection: close` закрывает соединение;
- HTTP/1.0 закрывается по умолчанию;
- `keepalive_timeout` защищает от клиентов, которые подключились и молчат;
- `keepalive_max_requests` ограничивает число запросов на одном соединении.

Для keep-alive обязательно отправлять корректный `Content-Length`, иначе клиент не поймет, где закончился ответ.

## Static files

`static/files.py` делает:

1. Берет URL path.
2. Декодирует URL через `unquote`.
3. Соединяет path с `root`.
4. Делает `.resolve()`.
5. Проверяет, что итоговый путь остался внутри `root`.
6. Если это файл, отдает его.
7. Если это каталог, ищет `index.html`.
8. Если `index.html` нет и `autoindex = on`, генерирует HTML-список файлов.

Защита от path traversal:

```python
candidate = (root / relative).resolve()
if root != candidate and root not in candidate.parents:
    return text_response(403, "Forbidden")
```

Так запрос `/../secret.txt` не сможет выйти за пределы `root`.

## Open file cache

`static/open_file_cache.py` хранит открытые файловые дескрипторы.

В записи кэша лежит:

- абсолютный путь;
- `fd`, то есть файловый дескриптор;
- размер файла;
- `mtime_ns`, время изменения;
- `last_used`, время последнего использования.

При запросе файла сервер:

1. Проверяет, есть ли файл в кэше.
2. Сверяет размер и `mtime_ns`.
3. Если файл не менялся, читает через `os.pread`.
4. Если файл изменился, закрывает старый fd и открывает заново.
5. Если кэш переполнен, удаляет самый давно неиспользованный элемент.

Это упрощенный аналог идеи nginx `open_file_cache`: меньше повторных `open/stat/close` для популярных файлов.

## Autoindex

`static/autoindex.py` генерирует простую HTML-страницу со списком файлов в каталоге.

`html.escape()` используется обязательно: имя файла может содержать символы вроде `<` или `"`, и их нельзя вставлять в HTML как есть.

## Virtual servers

Virtual server выбирается в `server/router.py` по заголовку `Host`.

Например:

```http
Host: demo.local
```

Если в конфиге есть server с `server_name = demo.local`, будет выбран он. Если точного совпадения нет, используется первый сервер как default.

Порт из `Host` отрезается: `localhost:8080` сравнивается как `localhost`.

## Location matching

Location выбирается по самому длинному подходящему prefix.

Для URL `/api/users` подходят `/` и `/api/`, но `/api/` длиннее, значит он точнее.

Это похоже на базовое prefix-matching поведение nginx.

## Proxy pass

`proxy/upstream.py` реализует простой reverse proxy:

1. Делит `proxy_pass` на один или несколько upstream URL.
2. Выбирает стартовый upstream по round-robin.
3. Разбирает URL через `urlparse`.
4. Открывает соединение к upstream через `asyncio.open_connection`.
5. Собирает новый HTTP/1.1-запрос.
6. Передает path, query, headers и body.
7. Переписывает `Host` на upstream.
8. Добавляет `X-Forwarded-For`.
9. Убирает hop-by-hop headers.
10. Читает ответ upstream и возвращает клиенту.

Если выбранный upstream не отвечает, соединение не открылось, истек timeout или ответ нельзя разобрать, proxy пробует следующий URL из того же `proxy_pass`. Если все upstream недоступны, клиент получает `502 Bad Gateway`.

Пример:

```ini
[location:local:/api/]
proxy_pass = http://127.0.0.1:9000 http://127.0.0.1:9001
```

Для простоты upstream-запрос отправляется с `Connection: close`. Это избавляет от необходимости держать отдельный пул keep-alive соединений к upstream.

Ограничение: chunked upstream response не разбирается, сервер попробует следующий upstream или вернет `502 Bad Gateway`, если других вариантов нет. Для учебной задачи это нормально, потому что базовый `python -m http.server` и большинство простых тестов используют `Content-Length`.

## SSL/HTTPS

HTTPS включается на уровне `server`:

```ini
[server:secure]
listen = 0.0.0.0:8443
server_name = secure.local
root = public
ssl = on
ssl_certfile = certs/server.crt
ssl_keyfile = certs/server.key
```

В `server/app.py` создается `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)`, загружается цепочка сертификата через `load_cert_chain()`, и этот context передается в `asyncio.start_server(..., ssl=context)`.

На одном `listen`-адресе все virtual servers должны быть либо обычными HTTP, либо HTTPS. SNI и разные сертификаты на одном порту не реализованы, чтобы код оставался простым.

## Access log

`logging.py` пишет строки формата:

```text
127.0.0.1 - - [23/May/2026:13:40:01 +0500] "GET / HTTP/1.1" 200 168 "-" "curl/8.0" 0.0012
```

Поля:

- IP клиента;
- дата;
- request line;
- status code;
- сколько bytes тела отправлено;
- referer;
- user-agent;
- время обработки.

Лог пишется после отправки ответа.

## Что поддерживается

- HTTP/1.0 и HTTP/1.1.
- `GET` и `HEAD` для статики.
- Любые методы для proxy, если тело задано через `Content-Length`.
- Keep-alive.
- Virtual hosts.
- Prefix locations.
- Static files.
- Autoindex.
- Open file cache.
- Access log.
- Proxy pass на HTTP upstream.
- Round-robin и failover для нескольких upstream.
- HTTPS/TLS для server.

## Что сознательно не реализовано

- HTTP/2 и HTTP/3.
- gzip/brotli.
- Chunked request body.
- Chunked upstream response.
- Полный синтаксис nginx config.
- Range requests.

Это нормальные ограничения для учебной версии: они не мешают показать архитектуру сервера.

## Ручная проверка

Обычная статика:

```bash
PYTHONPATH=src python3 -m pynginx --config config/pynginx.conf
curl -i http://127.0.0.1:8080/
```

Keep-alive, два запроса в одном TCP-соединении:

```bash
printf 'GET / HTTP/1.1\r\nHost: localhost\r\n\r\nGET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' | nc 127.0.0.1 8080
```

Autoindex:

```bash
mkdir -p public/files
echo hello > public/files/a.txt
curl -i http://127.0.0.1:8080/files/
```

Proxy:

```bash
mkdir -p upstream1/api upstream2/api
echo "from 9000" > upstream1/api/index.html
echo "from 9001" > upstream2/api/index.html
python3 -m http.server 9000 -d upstream1 &
python3 -m http.server 9001 -d upstream2 &
curl -i http://127.0.0.1:8080/api/
```

HTTPS:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout certs/server.key \
  -out certs/server.crt \
  -days 365 \
  -subj "/CN=localhost"
PYTHONPATH=src python3 -m pynginx --config config/ssl_demo.conf
curl -k -i https://127.0.0.1:8443/
```

Access log:

```bash
tail -f logs/access.log
```

Тесты:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
