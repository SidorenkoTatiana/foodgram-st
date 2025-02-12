Находясь в папке infra, выполните команду docker-compose up. При выполнении этой команды контейнер frontend, описанный в docker-compose.yml, подготовит файлы, необходимые для работы фронтенд-приложения, а затем прекратит свою работу.

[фронтенд веб-приложения] (http://localhost)
[спецификация API] (http://localhost/api/docs/)

[Автор: Сидоренко Татьяна] https://github.com/SidorenkoTatiana

[Проект] https://github.com/SidorenkoTatiana/foodgram-st

## Технологии:
* Python 3.10
* Django 3.2
* PostgreSQL
* DRF
* Docker
* Nginx

### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/SidorenkoTatiana/foodgram-st
```

```
cd foodgram-st
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv venv
```

```
source venv/Scripts/activate
(Для Linux: source venv/bin/activate)

```

```
python3 -m pip install --upgrade pip
```

Установить зависимости из файла requirements.txt:

```
cd backend/foodgram_backend
pip install -r requirements.txt
```

Выполнить миграции:

```
python3 manage.py migrate
```

Запустить проект:

(Из директории foodgram-st/)
```
docker compose up
```


Для дальнейшей работы, необходимо добавить список продуктов, которые будут использоваться в рецептах.
Список продуктов, уже подготовлен, он находится в папке - data/ingredients.csv
Добавление списка продуктов выполняется через Джанго-админку, кнопкой 'ИМПОРТ' во вкладке ингредиенты.