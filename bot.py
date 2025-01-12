import os
import json
import time
import requests
import telebot
import difflib
from transliterate import translit
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)
URL = os.getenv('URL')
SKIN_FILE = 'skins.json'
BLOCKLIST_FILE = 'blocklist.json'
IMAGES_FOLDER = 'Bundles'
INVENTORIES_DIR = 'inventories'
UPDATE_INTERVAL = 600
PERCENT = 0.8
api_data = []
last_update_time = 0
skins_from_skin_file = []

# Load blocklist
def load_blocklist():
    if os.path.exists(BLOCKLIST_FILE):
        with open(BLOCKLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Save blocklist
def save_blocklist(blocklist):
    with open(BLOCKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(blocklist, f, ensure_ascii=False, indent=4)

# Check if user is blocked
def is_user_blocked(user_id):
    blocklist = load_blocklist()
    return user_id in blocklist

# Add user to blocklist
def block_user(user_id):
    blocklist = load_blocklist()
    if user_id not in blocklist:
        blocklist.append(user_id)
        save_blocklist(blocklist)

# Remove user from blocklist
def unblock_user(user_id):
    blocklist = load_blocklist()
    if user_id in blocklist:
        blocklist.remove(user_id)
        save_blocklist(blocklist)

# Command to block a user
@bot.message_handler(commands=['block'])
def block_command_handler(message):
    if message.chat.type == 'private':
        user_id = message.from_user.id
        if user_id == 1781542224:  # Replace with your Telegram ID
            target_id = int(message.text.split()[1])
            block_user(target_id)
            bot.reply_to(message, f"Пользователь {target_id} заблокирован.")
        else:
            bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Command to unblock a user
@bot.message_handler(commands=['unblock'])
def unblock_command_handler(message):
    if message.chat.type == 'private':
        user_id = message.from_user.id
        if user_id == 1781542224:  # Replace with your Telegram ID
            target_id = int(message.text.split()[1])
            unblock_user(target_id)
            bot.reply_to(message, f"Пользователь {target_id} разблокирован.")
        else:
            bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

def load_skins():
    """Загружает данные о скинах."""
    global skins_from_skin_file
    with open(SKIN_FILE, 'r', encoding='utf-8') as f:
        skins_from_skin_file = json.load(f)

def fetch_skin_data_from_api():
    """Получает данные о скинах из API."""
    global api_data, last_update_time
    current_time = time.time()

    if current_time - last_update_time > UPDATE_INTERVAL:
        try:
            response = requests.get(URL)
            response.raise_for_status()
            api_data = response.json()
            last_update_time = current_time
            print("Данные API успешно обновлены.")
        except requests.RequestException as e:
            print(f"Ошибка при получении данных API: {e}")

    return api_data

def find_similar_skin(skins, skin_name, threshold=0.6):
    """Находит наиболее похожий скин по названию."""
    skin_names = [skin['name'].lower() for skin in skins]
    closest_matches = difflib.get_close_matches(skin_name.lower(), skin_names, n=1, cutoff=threshold)

    return next((skin for skin in skins if skin['name'].lower() == closest_matches[0]),
                None) if closest_matches else None

def find_similar_collection(skins, skin_name, threshold=0.6):
    """Находит наиболее похожую коллекцию по названию."""
    collection_names = [skin['collection'].lower() for skin in skins if 'collection' in skin]
    closest_matches = difflib.get_close_matches(skin_name.lower(), collection_names, n=1, cutoff=threshold)

    return closest_matches[0] if closest_matches else None

def transliterate_name(name):
    """Транслитерирует кириллическое имя в латиницу."""
    return translit(name, 'ru', reversed=True)

def rarity_mapping(value):
    """Возвращает редкость скина на основе его значения."""
    rarity_dict = {
        '1': 'Common',
        '2': 'Uncommon',
        '3': 'Rare',
        '4': 'Epic',
        '5': 'Legendary',
        '6': 'Arcane',
        '7': 'Nameless'
    }
    return rarity_dict.get(value, 'Containers')

def get_skin_info(skin, api_skin_info):
    """Создает отформатированную строку с информацией о скине."""
    info = f"Название: {skin['name']}\n"

    if 'contains' in skin:
        if api_skin_info:
            info += (f"Количество предложений: {api_skin_info.get('sales_count', 'Нет данных')}\n"
                     f"Количество запросов: {api_skin_info.get('purchases_count', 'Нет данных')}\n")
            info += f"Цена кейса: {api_skin_info.get('case_price', 'Нет данных')}\n" if 'case_price' in api_skin_info else f"Цена продажи: {api_skin_info.get('sale_price', 'Нет данных')}G\n"

        contained_ids = list(map(int, skin['contains'].split(',')))
        rarity_groups = {}

        for contained_skin_id in contained_ids:
            contained_skin = next((s for s in skins_from_skin_file if s['id'] == contained_skin_id), None)
            if contained_skin:
                value = str(contained_skin.get('value', '0')).strip().replace("'", "")
                rarity = rarity_mapping(value)
                rarity_groups.setdefault(rarity, []).append(contained_skin['name'])

        formatted_skins = [f"<b>{rarity}:</b>\n" + "\n".join(f"      {skin}" for skin in skins)+ "\n" for rarity, skins in
                           rarity_groups.items()]
        info += "Содержимое:<blockquote expandable>" + "\n".join(formatted_skins) + "</blockquote>"
    else:
        value = str(skin.get('value', '0')).strip().replace("'", "")
        rarity = rarity_mapping(value)
        collection = skin.get('collection', 'Нет данных').replace('_', ' ').replace('-', ' ').capitalize()
        info += (f"Коллекция: {collection}\n"
                 f"Редкость: {rarity}\n")

        if api_skin_info:
            info += (f"Количество предложений: {api_skin_info.get('sales_count', 'Нет данных')}\n"
                     f"Цена продажи: {api_skin_info.get('sale_price', 'Нет данных')}G\n"
                     f"Количество запросов: {api_skin_info.get('purchases_count', 'Нет данных')}\n"
                     f"Запрос: {api_skin_info.get('purchases_price', 'Нет данных')}G\n")

    return info


def send_skin_info(message, skin, api_skin_info):
    """Отправляет информацию о скине пользователю."""
    skin_id = skin['id']
    skin_info = get_skin_info(skin, api_skin_info)

    # Проверяем, является ли скин stattrack
    if 'stattrack' in skin['name'].lower():
        original_skin_name = skin['name'].lower().replace('stattrack', '').strip()
        original_skin = find_similar_skin(skins_from_skin_file, original_skin_name)
    # Формируем URL для изображения на GitHub
    image_url = f"https://raw.githubusercontent.com/Dinoger/UnionBot/refs/heads/main/Skin/{skin_id}.png?v={time.time()}"
    print(f"Sending photo for skin: {skin['name']} with URL: {image_url}")

    # Отправляем информацию о скине (оригинальном или stattrack)
    try:
        bot.send_photo(chat_id=message.chat.id, photo=image_url, caption=skin_info, parse_mode='HTML')
    except Exception as e:
        print(f"Error sending photo for skin {skin['name']}: {e}")

def process_skin_request(message, skin_name):
    """Обрабатывает запрос на скин от пользователя."""


    api_data = fetch_skin_data_from_api()
    skin = find_similar_skin(skins_from_skin_file, skin_name) or find_similar_skin(skins_from_skin_file,
                                                                                   transliterate_name(skin_name))

    if skin:
        skin_id = skin['id']
        api_skin_info = next((item for item in api_data if item['skin_id'] == str(skin_id)), None)
        send_skin_info(message, skin, api_skin_info)
    else:
        bot.reply_to(message, "Скин не найден.")

@bot.message_handler(commands=['skin'])
def skin_command_handler(message):
    if is_user_blocked(message.from_user.id):
        bot.reply_to(message, "Вы заблокированы и не можете использовать бота.")
        return
    """Обрабатывает команду /skin."""
    user_id = message.from_user.id
    print(f"Команда /skin от пользователя ID: {user_id}, имя: {message.from_user.username}")

    skin_name = ' '.join(message.text.split()[1:])
    process_skin_request(message, skin_name)


@bot.message_handler(commands=['start'])
def start_command_handler(message):
    """Обрабатывает команду /start."""
    user_id = message.from_user.id
    print(f"Команда /start от пользователя ID: {user_id}, имя: {message.from_user.username}")

    bot.reply_to(message, "Добро пожаловать!\n"
                          "Используйте команды /add для добавления скина, "
                          "/del для удаления скина, /info для получения информации об инвентаре, "
                          "и /skin для поиска информации о скине.")


@bot.message_handler(commands=['help'])
def help_command_handler(message):
    """Обрабатывает команду /help."""
    user_id = message.from_user.id
    print(f"Команда /help от пользователя ID: {user_id}, имя: {message.from_user.username}")

    bot.reply_to(message, "Вот список доступных команд:\n"
                          "/add <название_скина>: <количество> - Добавить скин в инвентарь.\n"
                          "/del <название_скина> - Удалить скин из инвентаря.\n"
                          "/inv - Получить информацию о вашем инвентаре.\n"
                          "/skin <название_скина> - Получить информацию о конкретном скине.")


@bot.inline_handler(lambda query: len(query.query) > 0)
def inline_skin_query(inline_query):
    """Обрабатывает инлайн запросы для поиска информации о скине."""
    skin_name = inline_query.query
    api_data = fetch_skin_data_from_api()
    skin = find_similar_skin(skins_from_skin_file, skin_name) or find_similar_skin(skins_from_skin_file,
                                                                                   transliterate_name(skin_name))

    if skin:
        skin_id = skin['id']
        api_skin_info = next((item for item in api_data if item['skin_id'] == str(skin_id)), None)
        skin_info = get_skin_info(skin, api_skin_info)

        # Проверяем, является ли скин StatTrak
        if 'stattrack' in skin['name'].lower():
            original_skin_name = skin['name'].lower().replace('stattrack', '').strip()
            original_skin = find_similar_skin(skins_from_skin_file, original_skin_name)
            # Если оригинальный скин найден, используем его ID для URL изображения
            if original_skin:
                skin_id = original_skin['id']  # Используем ID оригинального скина

        # Формируем URL для изображения на GitHub
        image_url = f"https://raw.githubusercontent.com/Dinoger/UnionBot/refs/heads/main/Skin/{skin_id}.png?v={time.time()}"

        # Создаем результат с изображением
        result = telebot.types.InlineQueryResultPhoto(
            id=skin_id,
            photo_url=image_url,  # URL изображения
            thumbnail_url=image_url,  # Миниатюра
            title=skin['name'],  # Заголовок
            description=skin_info,  # Описание
            caption=skin_info,  # Текст сообщения с информацией о скине
            parse_mode='HTML'  # Режим парсинга для текста
        )

        # Отправляем результат
        bot.answer_inline_query(inline_query.id, [result])
    else:
        bot.answer_inline_query(inline_query.id, [])

def get_inventory_info(skins):
    """Возвращает информацию об инвентаре и его общей стоимости."""
    api_data = fetch_skin_data_from_api()

    total_value = 0
    inventory_info = "Ваш инвентарь: <blockquote expandable>"

    for skin_name, quantity in skins.items():
        skin = find_similar_skin(skins_from_skin_file, skin_name)

        if skin:
            skin_id = skin['id']
            api_skin_info = next((item for item in api_data if item['skin_id'] == str(skin_id)), None)
            skin_value = api_skin_info['sale_price'] if api_skin_info else 0

            try:
                skin_value = float(skin_value)
            except (ValueError, TypeError):
                skin_value = 0

            total_value += skin_value * quantity
            inventory_info += (f"Скин: {skin['name']}\n"
                               f"Количество: {quantity}\n"
                               f"Цена за единицу: {skin_value:.2f}G\n"
                               f"При продаже: {skin_value * quantity * PERCENT:.2f}G\n\n")
        else:
            inventory_info += (f"Скин: {skin_name} (не найден в базе)\n"
                               f"Количество: {quantity}\n\n")

    inventory_info += f"</blockquote> Общая стоимость инвентаря: {total_value * PERCENT:.2f}G\n"

    return inventory_info, total_value

@bot.message_handler(commands=['inv'])
def inv_command_handler(message):
    if is_user_blocked(message.from_user.id):
        bot.reply_to(message, "Вы заблокированы и не можете использовать бота.")
        return
    """Обрабатывает команду /inv."""
    user_id = message.from_user.id
    print(f"Команда /inv от пользователя ID: {user_id}, имя: {message.from_user.username}")

    # Загружаем инвентарь пользователя
    inventory = load_json_file(user_id)

    if not inventory:
        bot.reply_to(message, "Ваш инвентарь пуст.")
        return

    # Получаем информацию об инвентаре
    inventory_info, total_value = get_inventory_info(inventory)

    # Отправляем информацию пользователю
    bot.reply_to(message, inventory_info, parse_mode='HTML')



def ensure_inventories_directory():
    """Убедиться, что папка Inventories существует."""
    if not os.path.exists(INVENTORIES_DIR):
        os.makedirs(INVENTORIES_DIR)

def get_inventory_file_path(user_id):
    """Возвращает путь к файлу инвентаря для данного пользователя."""
    return os.path.join(INVENTORIES_DIR, f"{user_id}_inventory.json")

def load_json_file(user_id):
    """Загружает JSON файл инвентаря пользователя."""
    ensure_inventories_directory()
    file_path = get_inventory_file_path(user_id)

    if not os.path.exists(file_path):
        return {}  # Возвращаем пустой инвентарь, если файл не существует

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read().strip()
        if not content:  # Проверка на пустой файл
            return {}  # Возвращаем пустой инвентарь, если файл пуст
        return json.loads(content)

def save_json_file(inventory, user_id):
    """Сохраняет JSON файл инвентаря пользователя."""
    ensure_inventories_directory()
    file_path = get_inventory_file_path(user_id)

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(inventory, file, ensure_ascii=False, indent=4)

def add_skin_to_inventory(user_id, skin_name, quantity):
    """Добавляет скин в инвентарь пользователя."""
    inventory = load_json_file(user_id)

    # Если инвентарь пустой, создаём новый словарь
    if not inventory:
        inventory = {}

    inventory[skin_name] = inventory.get(skin_name, 0) + quantity
    save_json_file(inventory, user_id)

def remove_skin_from_inventory(user_id, skin_name, quantity=None):
    """Удаляет скин из инвентаря пользователя."""
    inventory = load_json_file(user_id)

    if skin_name in inventory:
        if quantity is None:  # Если quantity не указано, удаляем все
            del inventory[skin_name]
            save_json_file(inventory, user_id)
            return True
        else:
            current_quantity = inventory[skin_name]
            if current_quantity >= quantity:
                inventory[skin_name] -= quantity
                if inventory[skin_name] == 0:
                    del inventory[skin_name]
                save_json_file(inventory, user_id)
                return True
            else:
                return False  # Недостаточно скинов для удаления
    return False  # Скин не найден в инвентаре


@bot.message_handler(commands=['add'])
def add_command_handler(message):
    if is_user_blocked(message.from_user.id):
        bot.reply_to(message, "Вы заблокированы и не можете использовать бота.")
        return
    if message.chat.type == 'private':
        """Обрабатывает команду /add."""
        user_id = message.from_user.id
        print(f"Команда /add от пользователя ID: {user_id}, имя: {message.from_user.username}\n")

        # Извлекаем текст после команды /add
        input_text = ' '.join(message.text.split()[1:]).strip()
        if ':' not in input_text:
            bot.reply_to(message, "Пожалуйста, используйте формат: /add <название_скина>: <количество>")
            return

        skin_name, quantity_str = map(str.strip, input_text.split(':', 1))

        skin = find_similar_skin(skins_from_skin_file, skin_name) or find_similar_skin(skins_from_skin_file,
                                                                                       transliterate_name(skin_name))

        try:
            quantity = int(quantity_str)
            if quantity <= 0 or quantity > 10000:
                bot.reply_to(message, "Количество скинов должно быть больше 0 и не превышать 10000. Пожалуйста, введите корректное число.")
                return
        except ValueError:
            bot.reply_to(message, "Пожалуйста, введите корректное количество скинов.")
            return

        if skin:
            bot.reply_to(message, f"Вы добавляете {quantity} скинов: {skin['name']}. Подтвердите (да/нет)?")
            bot.register_next_step_handler(message, lambda msg: confirm_addition(msg, skin, user_id, quantity))
        else:
            bot.reply_to(message, "Скин не найден.")

def confirm_addition(msg, skin, user_id, quantity):
    """Подтверждает добавление скина."""
    if msg.text.lower() == 'да':
        # Логика добавления скинов
        add_skin_to_inventory(user_id, skin['name'], quantity)  # Добавляем указанное количество скинов
        bot.reply_to(msg, f"Добавлено {quantity} скинов {skin['name']} в ваш инвентарь.")
    else:
        bot.reply_to(msg, "Добавление отменено.")

@bot.message_handler(commands=['del'])
def del_command_handler(message):
    if is_user_blocked(message.from_user.id):
        bot.reply_to(message, "Вы заблокированы и не можете использовать бота.")
        return
    if message.chat.type == 'private':
        """Обрабатывает команду /del."""
        user_id = message.from_user.id
        print(f"Команда /del от пользователя ID: {user_id}, имя: {message.from_user.username}")

        # Извлекаем текст после команды /del
        input_text = ' '.join(message.text.split()[1:]).strip()
        if ':' not in input_text:
            bot.reply_to(message, "Пожалуйста, используйте формат: /del <название_скина>: <количество>")
            return

        skin_name, quantity_str = map(str.strip, input_text.split(':', 1))

        skin = find_similar_skin(skins_from_skin_file, skin_name) or find_similar_skin(skins_from_skin_file,
                                                                                       transliterate_name(skin_name))

        try:
            quantity = int(quantity_str)
            if quantity <= 0 or quantity > 1000:
                bot.reply_to(message, "Количество скинов должно быть больше 0 и не превышать 1000. Пожалуйста, введите корректное число.")
                return
        except ValueError:
            bot.reply_to(message, "Пожалуйста, введите корректное количество скинов.")
            return

        if skin:
            bot.reply_to(message, f"Вы удаляете {quantity} скинов: {skin['name']}. Подтвердите (да/нет)?")
            bot.register_next_step_handler(message, lambda msg: confirm_removal(msg, skin, user_id, quantity))
        else:
            bot.reply_to(message, "Скин не найден.")

def confirm_removal(msg, skin, user_id, quantity):
    """Подтверждает удаление скина."""
    if msg.from_user.id != user_id:
        bot.reply_to(msg, "Пожалуйста, ответьте на запрос о удалении скина.")
        return

    if msg.text.lower() == 'да':
        # Логика удаления скинов
        if remove_skin_from_inventory(user_id, skin['name'], quantity):
            bot.reply_to(msg, f"Удалено {quantity} скинов {skin['name']} из вашего инвентаря.")
        else:
            bot.reply_to(msg, f"Недостаточно скинов {skin['name']} для удаления.")
    else:
        bot.reply_to(msg, "Удаление отменено.")


def rarity_order(rarity):
    """Возвращает порядковый номер редкости для сортировки."""
    order_dict = {
        'Common': 1,
        'Uncommon': 2,
        'Rare': 3,
        'Epic': 4,
        'Legendary': 5,
        'Arcane': 6,
        'Nameless': 7
    }
    return order_dict.get(rarity, float('inf'))

@bot.message_handler(commands=['col'])
def col_command_handler(message):
    if is_user_blocked(message.from_user.id):
        bot.reply_to(message, "Вы заблокированы и не можете использовать бота.")
        return

    """Обрабатывает команду /col."""
    user_id = message.from_user.id
    print(f"Команда /col от пользователя ID: {user_id}, имя: {message.from_user.username}")

    # Получаем название скина из текста сообщения
    skin_name = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not skin_name:
        bot.reply_to(message, "Пожалуйста, укажите название скина после команды /col.")
        return

    collection_name = find_similar_collection(skins_from_skin_file, skin_name) or find_similar_collection(skins_from_skin_file, transliterate_name(skin_name))
    if not collection_name:
        bot.reply_to(message, "Коллекция для данного скина не найдена.")
        return

    # Получаем информацию о скинах, исключая статтрек скины
    filtered_skins = [
        skin for skin in skins_from_skin_file
        if isinstance(skin.get('collection'), str)
        and skin['collection'].lower() == collection_name.lower()
        and 'stattrack' not in skin['name'].lower()  # Исключаем статтрек скины
    ]

    if not filtered_skins:
        bot.reply_to(message, "Скины для данной коллекции не найдены.")
        return

    # Получаем идентификаторы скинов из отфильтрованных скинов
    contained_ids = [skin['id'] for skin in filtered_skins]

    # Группируем скины по редкости на основе contained_ids
    rarity_groups = {}
    for contained_skin_id in contained_ids:
        contained_skin = next((s for s in skins_from_skin_file if s['id'] == contained_skin_id), None)
        if contained_skin:
            value = str(contained_skin.get('value', '0')).strip().replace("'", "")
            response = f"Скины в коллекции {collection_name}:<blockquote expandable>\n"
            if rarity_groups:
                sorted_rarities = sorted(rarity_groups.keys(), key=rarity_order)  # Сортируем редкости по порядку
                for rarity in sorted_rarities:
                    skins = rarity_groups[rarity]
                    response += f"<b>{rarity}:</b>\n" + "\n".join(f"      {skin}" for skin in skins) + "\n"
                response += "</blockquote>"
            else:
                response += "Скины не найдены по редкости."
            rarity = rarity_mapping(value)
            rarity_groups.setdefault(rarity, []).append(contained_skin['name'])

    # Формируем ответ, отображая редкости по очереди, отсортированные по редкости
    response = f"Скины в коллекции {collection_name}:<blockquote expandable>\n"
    if rarity_groups:
        sorted_rarities = sorted(rarity_groups.keys(), key=rarity_order)  # Сортируем редкости по порядку
        for rarity in sorted_rarities:
            skins = rarity_groups[rarity]
            response += f"<b>{rarity}:</b>\n" + "\n".join(f"      {skin}" for skin in skins) + "\n\n"
        response += "</blockquote>"
    else:
        response += "Скины не найдены по редкости."

    bot.reply_to(message, response, parse_mode='HTML')




if __name__ == "__main__":
    load_skins()
    bot.polling()
