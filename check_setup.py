"""
Проверка окружения перед запуском.
Запуск: python check_setup.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _key(name: str) -> str | None:
    v = os.getenv(name, "").strip()
    return v if v else None


def main() -> None:
    print("=== Investment Agent — проверка ===\n")
    print(f"Python: {sys.version.split()[0]}")

    missing = []
    for pkg in (
        "streamlit",
        "langchain",
        "langchain_groq",
        "yfinance",
        "matplotlib",
        "pandas",
    ):
        try:
            __import__(pkg)
            print(f"  OK  {pkg}")
        except ImportError:
            print(f"  --  {pkg} (не установлен)")
            missing.append(pkg)

    groq = _key("GROQ_API_KEY")
    serp = _key("SERPAPI_API_KEY")
    openai = _key("OPENAI_API_KEY")

    print("\nКлючи (.env или secrets.toml):")
    print(f"  GROQ_API_KEY:    {'да' if groq else 'нет — ReAct будет в шаблонном режиме'}")
    print(f"  SERPAPI_API_KEY: {'да' if serp else 'нет — новости через yfinance (бесплатно)'}")
    print(f"  OPENAI_API_KEY:  {'да' if openai else 'нет'}")

    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.isfile(secrets_path):
        print(f"\n  Найден {secrets_path}")
    else:
        print(f"\n  Создайте {secrets_path} из secrets.toml.example")

    if missing:
        print("\nУстановите зависимости: pip install -r requirements.txt")
        sys.exit(1)

    if groq:
        print("\nГотово к запуску: streamlit run app.py")
    else:
        print("\nЗапуск возможен, но добавьте GROQ_API_KEY для AI-отчёта.")
    print("Деплой + APK: см. DEPLOY_AND_WEBVIEW.md")


if __name__ == "__main__":
    main()
