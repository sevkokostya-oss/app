# Подключение веб-приложения и сборка APK (WebView)

## Шаг 0 — безопасность ключа Groq

Если ключ когда-либо отправляли в чат или в GitHub:

1. Откройте https://console.groq.com → API Keys  
2. **Удалите** старый ключ и создайте **новый**  
3. Вставьте только в `.streamlit/secrets.toml` или `.env` на своём ПК  

---

## Шаг 1 — локально (проверка)

```powershell
cd investment_agent
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Создайте `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "gsk_ВАШ_НОВЫЙ_КЛЮЧ"
SERPAPI_API_KEY = ""
OPENAI_API_KEY = ""
```

Проверка:

```powershell
python check_setup.py
streamlit run app.py
```

В браузере: введите `NVDA` → «Анализировать». В сайдбаре должно быть: **Groq: подключён**.

**SerpAPI не обязателен** — новости идут через yfinance бесплатно.

---

## Шаг 2 — выложить в интернет (для WebView нужен URL)

### Вариант A: Streamlit Community Cloud (бесплатно)

1. Залейте папку `investment_agent` на **GitHub** (репозиторий).  
2. https://share.streamlit.io → New app  
3. Repository + ветка `main`, файл: **`app.py`**  
4. В **Settings → Secrets** добавьте:

```toml
GROQ_API_KEY = "gsk_..."
```

5. Deploy → скопируйте URL, например:  
   `https://investment-agent-sevko.streamlit.app`

### Вариант B: только на своём ПК (для APK не подходит)

WebView на телефоне не увидит `localhost` с вашего ПК без туннеля (ngrok). Для APK используйте **Streamlit Cloud**.

---

## Шаг 3 — WebView APK

1. Установите **Android Studio**  
2. Откройте папку `android_webview/`  
3. В файле  
   `app/src/main/res/values/strings.xml`  
   замените:

```xml
<string name="web_app_url">https://YOUR_APP.streamlit.app</string>
```

на ваш реальный URL из шага 2.

4. **Build → Build APK(s)**  
5. APK: `app/build/outputs/apk/debug/app-debug.apk`

Установите на телефон. Приложение — это окно, которое открывает ваше Streamlit-приложение в интернете.

---

## Что вам ещё нужно (чеклист)

| Нужно | Обязательно? |
|-------|----------------|
| **GROQ_API_KEY** (новый, после отзыва старого) | Да, для AI-отчёта |
| **Python 3.10+** | Да, для локальной проверки |
| **GitHub аккаунт** | Да, для Streamlit Cloud |
| **Интернет на телефоне** | Да, WebView грузит сайт |
| **Android Studio** | Да, для сборки APK |
| SERPAPI_API_KEY | Нет |
| OPENAI_API_KEY | Нет |

---

## Порядок работы (кратко)

```
Локально secrets.toml → streamlit run → тест NVDA
        ↓
GitHub → Streamlit Cloud + Secrets → получить URL
        ↓
android_webview/strings.xml → URL → Build APK
```
