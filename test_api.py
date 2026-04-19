"""
Диагностический скрипт — запустите его чтобы найти причину ошибки.
Запуск: python test_api.py
"""

import os
import requests
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

print("=" * 50)
print("ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ К API")
print("=" * 50)

# ── Проверка 1: ключ загружен? ──────────────────
print("\n[1] Проверка API-ключа...")
if not API_KEY:
    print("❌ Ключ НЕ загружен из .env")
    print("   → Убедитесь что файл .env существует")
    print("   → Содержимое: OPENWEATHER_API_KEY=ваш_ключ")
elif API_KEY == "YOUR_API_KEY" or API_KEY == "ваш_ключ_сюда":
    print("❌ Ключ не заменён — вы оставили placeholder")
    print("   → Замените на реальный ключ с openweathermap.org")
elif len(API_KEY) != 32:
    print(f"⚠️  Подозрительная длина ключа: {len(API_KEY)} символов")
    print("   → Обычный ключ OpenWeatherMap = 32 символа")
    print(f"   → Ваш ключ: {API_KEY[:6]}...{API_KEY[-4:]}")
else:
    print(f"✅ Ключ загружен: {API_KEY[:6]}...{API_KEY[-4:]}")
    print(f"   Длина: {len(API_KEY)} символов")

# ── Проверка 2: интернет работает? ─────────────
print("\n[2] Проверка интернет-соединения...")
try:
    r = requests.get("https://google.com", timeout=5)
    print("✅ Интернет работает")
except requests.exceptions.ConnectionError:
    print("❌ Нет подключения к интернету")
    print("   → Проверьте Wi-Fi или кабель")
except requests.exceptions.Timeout:
    print("⚠️  Соединение есть, но google.com не отвечает")

# ── Проверка 3: API доступен? ──────────────────
print("\n[3] Проверка доступности OpenWeatherMap...")
try:
    r = requests.get("https://openweathermap.org", timeout=5)
    print(f"✅ Сайт доступен (код: {r.status_code})")
except Exception as e:
    print(f"❌ Сайт недоступен: {e}")

# ── Проверка 4: тестовый запрос к API ──────────
print("\n[4] Тестовый запрос к API (Москва)...")
if API_KEY and API_KEY not in ("YOUR_API_KEY", "ваш_ключ_сюда"):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": 55.7558,
        "lon": 37.6173,
        "appid": API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        code = response.status_code

        if code == 200:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            print(f"✅ Успех! Москва: {temp}°C, {desc}")
            print("\n🎉 API работает корректно!")
            print("   Перезапустите app.py и попробуйте снова.")

        elif code == 401:
            print("❌ Ошибка 401 — Неверный API-ключ")
            print("   Возможные причины:")
            print("   → Ключ скопирован с ошибкой (лишний пробел?)")
            print("   → Ключ ещё не активирован (ждите 15-30 минут)")
            print("   → Ключ был удалён или деактивирован")
            print(f"\n   Ваш ключ: [{API_KEY}]")

        elif code == 429:
            print("❌ Ошибка 429 — Превышен лимит запросов")
            print("   → Бесплатный план: 60 запросов/минуту")
            print("   → Подождите несколько минут")

        elif code == 404:
            print("❌ Ошибка 404 — Город не найден")

        else:
            print(f"❌ Неожиданный код: {code}")
            print(f"   Ответ: {data}")

    except requests.exceptions.Timeout:
        print("❌ Превышено время ожидания (10 сек)")
        print("   → Медленный интернет или API недоступен")
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка соединения с api.openweathermap.org")
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")
else:
    print("⏭️  Пропущено — сначала исправьте API-ключ")

print("\n" + "=" * 50)