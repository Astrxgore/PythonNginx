# Шпаргалка по функциям и конструкциям

Краткий справочник по тому, что используется в проекте.

## Python

`dataclass`
: Автоматически создает `__init__` и удобное хранение данных. Используется для конфигов, request, response.

`slots=True`
: Запрещает динамически добавлять новые поля объекту и немного экономит память.

`Path`
: Объектная работа с путями: `root / "index.html"`, `.resolve()`, `.parents`.

`dict.get(key, default)`
: Безопасно получить значение из словаря, не падая с `KeyError`.

`field(default_factory=list)`
: Правильный способ задать пустой список по умолчанию в dataclass.

`with TemporaryDirectory()`
: Создает временную папку для теста и сам удаляет ее после выхода из блока.

`async def`
: Объявляет coroutine-функцию. Она может использовать `await`.

`await`
: Приостанавливает текущую coroutine до готовности результата и дает event loop шанс выполнять другие задачи.

`asyncio.start_server`
: Запускает TCP-сервер. На каждое подключение вызывает handler.

`asyncio.open_connection`
: Открывает TCP-соединение как клиент.

`ssl.SSLContext`
: Настраивает TLS для HTTPS-сервера. В проекте используется `ssl.PROTOCOL_TLS_SERVER` и `load_cert_chain()`.

`asyncio.wait_for`
: Ограничивает время ожидания операции.

`asyncio.to_thread`
: Выполняет блокирующую функцию в отдельном потоке.

`StreamReader.readuntil`
: Читает из TCP-потока до заданного разделителя.

`StreamReader.readexactly`
: Читает строго N байт. Удобно для `Content-Length`.

`StreamWriter.write`
: Кладет bytes в буфер отправки.

`StreamWriter.drain`
: Ждет, пока буфер можно продолжать заполнять.

`urlsplit`
: Разбирает URL на path, query и другие части.

`unquote`
: Декодирует URL encoding: `%20` превращается в пробел.

`mimetypes.guess_type`
: Определяет `Content-Type` по имени файла.

`formatdate(usegmt=True)`
: Формирует HTTP-совместимую дату для headers.

`html.escape`
: Экранирует строки перед вставкой в HTML.

`os.open`
: Низкоуровнево открывает файл и возвращает fd.

`os.pread`
: Читает из fd с указанной позиции, не меняя текущую позицию файла.

`os.close`
: Закрывает fd.

`time.monotonic`
: Монотонное время для измерения timeout/elapsed, не зависит от перевода системных часов.

`logging.FileHandler`
: Записывает log-сообщения в файл.

`unittest.TestCase`
: Базовый класс тестов из стандартной библиотеки.

`unittest.IsolatedAsyncioTestCase`
: Позволяет писать async-тесты без сторонних библиотек.

## HTTP

Request line
: Первая строка запроса: `GET /path HTTP/1.1`.

Method
: Действие: `GET`, `HEAD`, `POST`.

Target
: Часть запроса после метода: `/index.html` или `/api?q=1`.

Headers
: Метаданные запроса или ответа: `Host`, `Content-Length`, `Connection`.

Body
: Тело запроса или ответа. У `GET` обычно отсутствует.

`Host`
: Заголовок, по которому выбирается virtual server.

`Content-Length`
: Размер body в байтах.

`Connection: close`
: Просьба закрыть TCP-соединение после ответа.

Keep-alive
: Несколько HTTP-запросов через одно TCP-соединение.

Status code
: Код ответа: `200`, `404`, `502`.

`HEAD`
: Как `GET`, но сервер отправляет только headers без body.

`Last-Modified`
: Время последнего изменения файла.

`Content-Type`
: Тип тела ответа: `text/html`, `text/plain`, `image/png`.

`301 Moved Permanently`
: Redirect. В проекте используется для URL каталога без `/`.

`403 Forbidden`
: Сервер понял запрос, но запрещает доступ.

`404 Not Found`
: Файл или route не найден.

`405 Method Not Allowed`
: Метод не поддерживается для статики.

`431 Request Header Fields Too Large`
: Заголовки слишком большие.

`502 Bad Gateway`
: Proxy не смог получить нормальный ответ от upstream.

Reverse proxy
: Сервер принимает запрос от клиента и пересылает его другому HTTP-серверу.

Upstream
: Сервер, к которому proxy пересылает запрос.

Load balancing
: Распределение запросов между несколькими upstream. В проекте используется простой round-robin.

Hop-by-hop headers
: Headers, действующие только на одно соединение. Proxy удаляет их при пересылке.
