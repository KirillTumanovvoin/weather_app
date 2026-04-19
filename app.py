"""
Веб-приложение «Оденься по погоде»
Показывает погоду, местное время и рекомендации по одежде
для 11 городов России в разных часовых поясах.
"""

import json
import logging
import os
from datetime import datetime

import pytz
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for

# ──────────────────────────────────────────────
# Загрузка переменных окружения из файла .env
# ──────────────────────────────────────────────
load_dotenv()

# ──────────────────────────────────────────────
# Константы
# ──────────────────────────────────────────────
API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_TIMEOUT = 5          # секунды ожидания ответа от API
CITIES_FILE = "cities.json"  # путь к файлу с городами

# ──────────────────────────────────────────────
# Настройка логирования
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Инициализация Flask
# ──────────────────────────────────────────────
app = Flask(__name__)


# ══════════════════════════════════════════════
# Вспомогательные функции
# ══════════════════════════════════════════════

def load_cities() -> dict:
    """
    Загружает список городов из файла cities.json.

    Returns:
        dict: словарь с данными городов или пустой словарь при ошибке.
    """
    try:
        with open(CITIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Файл %s не найден.", CITIES_FILE)
        return {}
    except json.JSONDecodeError as e:
        logger.error("Ошибка чтения JSON: %s", e)
        return {}


def get_weather(city_data: dict) -> dict | None:
    """
    Запрашивает текущую погоду через OpenWeatherMap API.

    Args:
        city_data (dict): словарь с ключами lat, lon.

    Returns:
        dict: данные о погоде или None при ошибке.
    """
    if not API_KEY:
        logger.warning("API-ключ не задан. Проверьте файл .env")
        return None

    params = {
        "lat": city_data["lat"],
        "lon": city_data["lon"],
        "appid": API_KEY,
        "units": "metric",   # температура в градусах Цельсия
        "lang": "ru",        # описание погоды на русском
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        # Вызываем исключение при кодах 4xx / 5xx
        response.raise_for_status()
        data = response.json()
        logger.info(
            "Погода успешно получена: %s, %.1f°C",
            data.get("weather", [{}])[0].get("description", ""),
            data.get("main", {}).get("temp", 0)
        )
        return data

    except requests.exceptions.Timeout:
        logger.error("Превышено время ожидания ответа от API.")
    except requests.exceptions.ConnectionError:
        logger.error("Нет подключения к интернету.")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        if status == 401:
            logger.error("Неверный API-ключ (401).")
        elif status == 429:
            logger.error("Превышен лимит запросов (429).")
        else:
            logger.error("HTTP-ошибка: %s", status)
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error("Непредвиденная ошибка запроса: %s", e)

    return None


def get_local_time(timezone_str: str) -> dict:
    """
    Возвращает текущее локальное время для заданного часового пояса.

    Args:
        timezone_str (str): строка вида 'Asia/Vladivostok'.

    Returns:
        dict: ключи time (HH:MM), date (дата), utc_offset (±ЧЧ:ММ).
    """
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)

        # Смещение UTC в формате ±ЧЧ:ММ
        offset = now.strftime("%z")          # '+0300'
        utc_offset = f"UTC{offset[:3]}:{offset[3:]}"  # 'UTC+03:00'

        return {
            "time": now.strftime("%H:%M"),
            "date": now.strftime("%d %B %Y"),
            "hour": now.hour,
            "utc_offset": utc_offset,
        }
    except pytz.UnknownTimeZoneError:
        logger.error("Неизвестный часовой пояс: %s", timezone_str)
        return {
            "time": "--:--",
            "date": "Неизвестно",
            "hour": 12,
            "utc_offset": "UTC?",
        }


def get_season(month: int) -> str:
    """
    Определяет сезон по номеру месяца (для Северного полушария).

    Args:
        month (int): номер месяца от 1 до 12.

    Returns:
        str: 'зима', 'весна', 'лето' или 'осень'.
    """
    if month in (12, 1, 2):
        return "зима"
    elif month in (3, 4, 5):
        return "весна"
    elif month in (6, 7, 8):
        return "лето"
    else:
        return "осень"


def get_time_of_day(hour: int) -> str:
    """
    Определяет часть суток по текущему часу.

    Args:
        hour (int): час от 0 до 23.

    Returns:
        str: 'ночь', 'утро', 'день' или 'вечер'.
    """
    if 0 <= hour < 6:
        return "ночь"
    elif 6 <= hour < 12:
        return "утро"
    elif 12 <= hour < 18:
        return "день"
    else:
        return "вечер"


def get_clothing_recommendation(
    temp: float,
    time_of_day: str,
    season: str,
    description: str
) -> dict:
    """
    Формирует рекомендации по одежде на основе погодных условий.

    Args:
        temp (float): температура воздуха в °C.
        time_of_day (str): часть суток ('утро', 'день', 'вечер', 'ночь').
        season (str): текущий сезон ('зима', 'весна', 'лето', 'осень').
        description (str): описание погоды от API (дождь, снег и т. д.).

    Returns:
        dict: ключи items (список одежды), tip (дополнительный совет),
              emoji (иконка), level (уровень тепла).
    """
    # Ключевые слова для определения осадков
    desc_lower = description.lower()
    is_rain = any(w in desc_lower for w in ["дождь", "ливень", "морось"])
    is_snow = any(w in desc_lower for w in ["снег", "метель", "вьюга"])
    is_wind = "ветер" in desc_lower

    # ── Очень сильный мороз (ниже −30 °C) ──────────────────
    if temp < -30:
        items = [
            "Термобельё (первый слой)",
            "Шерстяной свитер (второй слой)",
            "Пуховик или арктическая парка",
            "Тёплые зимние брюки",
            "Меховая шапка + балаклава",
            "Шарф (закрывает лицо)",
            "Варежки-краги поверх перчаток",
            "Зимние сапоги (-40 °C и ниже)",
            "Тёплые носки (шерсть или термо)",
        ]
        tip = (
            "🚨 Экстремальный холод! Открытые участки кожи "
            "могут получить обморожение за 5–10 минут. "
            "По возможности оставайтесь дома."
        )
        emoji = "🥶"
        level = "arctic"

    # ── Сильный мороз (−30 … −10 °C) ──────────────────────
    elif temp < -10:
        items = [
            "Термобельё",
            "Флисовый или шерстяной свитер",
            "Тёплый зимний пуховик",
            "Утеплённые брюки",
            "Шапка-ушанка или лыжная шапка",
            "Шарф или снуд",
            "Утеплённые перчатки или варежки",
            "Зимние ботинки или сапоги",
        ]
        if is_snow:
            items.append("Непромокаемые бахилы или гамаши")
        tip = (
            "❄️ Одевайтесь слоями: термобельё → утеплитель → "
            "ветрозащитная верхняя одежда."
        )
        emoji = "🧥"
        level = "very_cold"

    # ── Холодно (−10 … +5 °C) ──────────────────────────────
    elif temp < 5:
        items = [
            "Тёплый свитер или флис",
            "Зимняя или демисезонная куртка",
            "Джинсы или утеплённые брюки",
            "Шапка",
            "Перчатки",
            "Шарф",
            "Закрытая обувь на тёплой подкладке",
        ]
        if is_rain or is_snow:
            items.insert(2, "Водонепроницаемая верхняя одежда")
            items.append("Зонт или капюшон")
        tip = (
            "🧣 Не забудьте шапку — через голову теряется "
            "значительная часть тепла."
        )
        emoji = "🧤"
        level = "cold"

    # ── Прохладно (+5 … +15 °C) ────────────────────────────
    elif temp < 15:
        items = [
            "Лёгкий свитер или толстовка",
            "Демисезонная куртка или плащ",
            "Джинсы или плотные брюки",
            "Закрытая обувь",
        ]
        if is_rain:
            items.insert(2, "Водонепроницаемый плащ или куртка")
            items.append("Зонт")
        if time_of_day in ("вечер", "ночь"):
            items.insert(0, "Лёгкий тёплый свитер (вечером холоднее)")
        tip = (
            "🌤️ Возьмите куртку с собой — "
            "днём может быть теплее, а вечером прохладнее."
        )
        emoji = "🧥"
        level = "cool"

    # ── Тепло (+15 … +25 °C) ───────────────────────────────
    elif temp < 25:
        items = [
            "Футболка или рубашка",
            "Лёгкие брюки, джинсы или юбка",
            "Кроссовки или лёгкая обувь",
        ]
        if is_rain:
            items.append("Лёгкий дождевик или зонт")
        if season == "весна" or time_of_day in ("вечер", "ночь"):
            items.insert(2, "Лёгкая кофта или кардиган (на вечер)")
        tip = (
            "😊 Комфортная погода! Одевайтесь легко, "
            "но возьмите что-нибудь потеплее на вечер."
        )
        emoji = "👕"
        level = "warm"

    # ── Жарко (+25 °C и выше) ──────────────────────────────
    else:
        items = [
            "Лёгкая футболка или топ (светлые цвета)",
            "Шорты, лёгкие брюки или платье",
            "Открытая обувь: сандалии, кроссовки",
            "Солнцезащитные очки",
            "Головной убор (панама, кепка)",
        ]
        if is_rain:
            items.append("Компактный зонт")
        tip = (
            "☀️ Не забывайте наносить солнцезащитный крем (SPF 30+) "
            "и пить достаточно воды."
        )
        emoji = "🌞"
        level = "hot"

    # Дополнительный совет при сильном ветре
    if is_wind and level not in ("arctic", "very_cold"):
        tip += " 💨 Ветрено — выбирайте ветрозащитную верхнюю одежду."

    return {
        "items": items,
        "tip": tip,
        "emoji": emoji,
        "level": level,
    }


def parse_weather_data(raw: dict) -> dict:
    """
    Извлекает нужные поля из ответа OpenWeatherMap.

    Args:
        raw (dict): «сырой» JSON-ответ от API.

    Returns:
        dict: подготовленные данные для шаблона.
    """
    main = raw.get("main", {})
    wind = raw.get("wind", {})
    weather_list = raw.get("weather", [{}])

    return {
        "temp": round(main.get("temp", 0)),
        "feels_like": round(main.get("feels_like", 0)),
        "humidity": main.get("humidity", 0),
        "pressure": round(main.get("pressure", 0) * 0.750064),  # гПа → мм рт. ст.
        "wind_speed": round(wind.get("speed", 0)),
        "description": weather_list[0].get("description", "Нет данных"),
        "icon_code": weather_list[0].get("icon", "01d"),
        "visibility": round(raw.get("visibility", 0) / 1000, 1),  # м → км
    }


# ══════════════════════════════════════════════
# Маршруты (routes)
# ══════════════════════════════════════════════

@app.route("/")
def index():
    """Главная страница — список городов для выбора."""
    cities = load_cities()
    return render_template("index.html", cities=cities)


@app.route("/weather/<city_name>")
def weather(city_name: str):
    """
    Страница с погодой для выбранного города.

    Args:
        city_name (str): название города из URL (совпадает с ключом в JSON).
    """
    cities = load_cities()

    # ── Валидация входных данных ──────────────────────────────
    if city_name not in cities:
        logger.warning("Запрошен неизвестный город: %s", city_name)
        return render_template(
            "city_weather.html",
            error=f"Город «{city_name}» не найден в списке.",
            city_name=city_name,
            cities=cities,
        ), 404

    city_data = cities[city_name]

    # ── Получение данных ──────────────────────────────────────
    raw_weather = get_weather(city_data)
    local_time = get_local_time(city_data["tz"])

    if raw_weather is None:
        # Graceful деградация: показываем страницу с сообщением об ошибке
        return render_template(
            "city_weather.html",
            error=(
                "Не удалось получить данные о погоде. "
                "Проверьте API-ключ или соединение с интернетом."
            ),
            city_name=city_name,
            city_emoji=city_data.get("emoji", "🏙️"),
            local_time=local_time,
            cities=cities,
        )

    # ── Обработка данных ──────────────────────────────────────
    weather_info = parse_weather_data(raw_weather)

    current_month = datetime.now(
        pytz.timezone(city_data["tz"])
    ).month
    season = get_season(current_month)
    time_of_day = get_time_of_day(local_time["hour"])

    clothing = get_clothing_recommendation(
        temp=weather_info["temp"],
        time_of_day=time_of_day,
        season=season,
        description=weather_info["description"],
    )

    # ── Сборка контекста для шаблона ─────────────────────────
    data = {
        "city_name": city_name,
        "city_emoji": city_data.get("emoji", "🏙️"),
        "local_time": local_time,
        "season": season,
        "time_of_day": time_of_day,
        "weather": weather_info,
        "clothing": clothing,
        "icon_url": (
            f"https://openweathermap.org/img/wn/"
            f"{weather_info['icon_code']}@2x.png"
        ),
    }

    return render_template("city_weather.html", data=data, cities=cities)


@app.route("/about")
def about():
    """Страница 'О проекте'."""
    return render_template("index.html", cities=load_cities(), show_about=True)


# ── Обработчики ошибок ────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    """Страница 404."""
    return render_template(
        "city_weather.html",
        error="Страница не найдена.",
        cities=load_cities()
    ), 404


@app.errorhandler(500)
def server_error(error):
    """Страница 500."""
    logger.exception("Внутренняя ошибка сервера")
    return render_template(
        "city_weather.html",
        error="Внутренняя ошибка сервера. Попробуйте позже.",
        cities=load_cities()
    ), 500


# ══════════════════════════════════════════════
# Точка входа
# ══════════════════════════════════════════════

if __name__ == "__main__":
    if not API_KEY:
        logger.warning(
            "⚠️  API-ключ не задан! Создайте файл .env "
            "и добавьте OPENWEATHER_API_KEY=ваш_ключ"
        )
    app.run(debug=True, host="0.0.0.0", port=5000)