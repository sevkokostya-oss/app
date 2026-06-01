# Инвестиционный AI-агент

## Сейчас (локально)

1. В `.streamlit/secrets.toml` укажите **новый** `GROQ_API_KEY` (не публикуйте в чат).
2. `pip install -r requirements.txt`
3. `python check_setup.py`
4. `streamlit run app.py` или двойной клик `run_local.bat`

## Потом (веб + APK)

Пошагово: **[DEPLOY_AND_WEBVIEW.md](DEPLOY_AND_WEBVIEW.md)**

- Streamlit Cloud → публичный URL  
- `android_webview/` → подставить URL → собрать APK  
