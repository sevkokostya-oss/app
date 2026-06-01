"""
Общие настройки приложения (локально и для документации WebView).
URL веб-приложения задаётся после деплоя на Streamlit Cloud.
"""

import os

# После деплоя подставьте сюда или в android .../strings.xml
# Пример: https://investment-agent-xxx.streamlit.app
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://YOUR_APP.streamlit.app")
