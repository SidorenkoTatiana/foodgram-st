import json
import psycopg2

# Подключение к базе данных
connection = psycopg2.connect(
    dbname='django',
    user='django_user',
    password='mysecretpassword',  # Убедитесь, что вы используете правильный пароль
    host='db',  # Имя сервиса из docker-compose
    port='5432'
)

cursor = connection.cursor()

# Чтение данных из JSON файла
with open('data/ingredients.json', 'r', encoding='utf-8') as file:
    ingredients = json.load(file)

# Вставка данных в таблицу
for ingredient in ingredients:
    cursor.execute(
        "INSERT INTO recipes_ingredient (name, measurement_unit) VALUES (%s, %s)",
        (ingredient['name'], ingredient['measurement_unit'])
    )

# Подтверждение изменений и закрытие соединения
connection.commit()
cursor.close()
connection.close()
