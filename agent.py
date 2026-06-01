"""
Investment Idea Analyzer — LangChain ReAct agent.

LLM priority (all have free tiers):
  1. Groq — https://console.groq.com (free API key)
  2. OpenAI — if OPENAI_API_KEY is set
  3. Template report — no key required (demo mode)
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

try:
    from langchain.agents import AgentExecutor, create_react_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_react_agent

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from tools import get_stock_financials, search_news

SYSTEM_ANALYST_RULES = """
Ты — финансовый аналитик-исследователь (Investment Idea Analyzer).
Ты отвечаешь ТОЛЬКО на основе данных из инструментов и приложенного контекста.

СТРОГИЕ ПРАВИЛА:
- Никогда не рекомендуй покупать, продавать или держать акции.
- Не давай прогнозов цены и целевых уровней.
- Перечисляй факты, метрики и контекст из новостей.
- Для каждой новости указывай источник и ссылку.
- Если данных нет — явно напиши об этом.
- Пиши отчёт на русском языке, структурированно.
- В конце отчёта обязательно добавь фразу:
  «Это не инвестиционная рекомендация. Информация носит аналитический характер.»

Структура финального отчёта (используй заголовки ##):
## Новостной фон
## Финансовые показатели
## Мультипликаторы
## Риски
## Итог (только факты, без советов)
"""

REACT_TEMPLATE = SYSTEM_ANALYST_RULES + """

У тебя есть инструменты:
{tools}

Имена инструментов: {tool_names}

Алгоритм:
1. Сначала вызови get_stock_financials для тикера.
2. Затем вызови search_news с запросом «<TICKER> stock news last 7 days».
3. На основе полученных JSON сформируй финальный отчёт по структуре выше.

Формат ReAct:
Question: входной вопрос
Thought: твои рассуждения
Action: имя инструмента
Action Input: вход инструмента
Observation: результат
... (повторяй Thought/Action/Observation при необходимости)
Thought: I now know the final answer
Final Answer: полный отчёт на русском

Question: {input}
Thought: {agent_scratchpad}
"""


def _get_secret(key: str) -> str | None:
    """Read non-empty secret from Streamlit secrets or environment."""
    val: str | None = None
    try:
        import streamlit as st

        if key in st.secrets:
            val = str(st.secrets[key])
    except Exception:
        pass
    if not val:
        val = os.getenv(key)
    if val and str(val).strip() and str(val).strip() not in ('""', "''"):
        return str(val).strip().strip('"').strip("'")
    return None


def is_groq_configured() -> bool:
    return bool(_get_secret("GROQ_API_KEY"))


def build_llm() -> BaseChatModel | None:
    """
    Build chat model from free/cheap providers.
    Returns None if no API key — app will use template fallback.
    """
    groq_key = _get_secret("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq

            return ChatGroq(
                model="llama-3.1-8b-instant",
                temperature=0.2,
                groq_api_key=groq_key,
            )
        except Exception:
            pass

    openai_key = _get_secret("OPENAI_API_KEY")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.2,
                api_key=openai_key,
            )
        except Exception:
            pass

    return None


class AgentThoughtLogger(BaseCallbackHandler):
    """Collect ReAct steps for Streamlit expander."""

    def __init__(self) -> None:
        self.steps: list[str] = []
        self._status_callback: Any = None

    def set_status_callback(self, fn: Any) -> None:
        self._status_callback = fn

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        name = serialized.get("name", "tool")
        line = f"🔧 Инструмент: **{name}** — вход: `{input_str[:120]}`"
        self.steps.append(line)
        if self._status_callback:
            if name == "search_news":
                self._status_callback("Ищу новости...")
            elif name == "get_stock_financials":
                self._status_callback("Загружаю финансы...")

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        self.steps.append(f"💭 Thought → Action: **{action.tool}**")

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        self.steps.append("✅ Агент завершил рассуждение.")


def prefetch_parallel(ticker: str) -> tuple[str, str]:
    """Run financials + news tools in parallel (for UI status + fallback)."""
    news_query = f"{ticker} stock news last 7 days"

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_fin = pool.submit(get_stock_financials.invoke, {"ticker": ticker})
        f_news = pool.submit(search_news.invoke, {"query": news_query})
        financials = f_fin.result()
        news = f_news.result()
    return financials, news


def _template_report(ticker: str, financials_json: str, news_json: str) -> str:
    """Free fallback report without LLM API."""
    try:
        fin = json.loads(financials_json)
    except json.JSONDecodeError:
        fin = {"error": financials_json}
    try:
        news_data = json.loads(news_json)
    except json.JSONDecodeError:
        news_data = {"articles": []}

    if fin.get("error"):
        return f"## Ошибка\n{fin['error']}\n\n*Это не инвестиционная рекомендация.*"

    lines = [
        f"# Аналитический обзор: {fin.get('company_name', ticker)} ({fin.get('ticker', ticker)})",
        "",
        "## Новостной фон",
    ]
    articles = news_data.get("articles") or []
    if not articles:
        lines.append("Новости за последнюю неделю не найдены.")
    else:
        for i, a in enumerate(articles, 1):
            lines.append(
                f"{i}. **{a.get('title', '')}** — {a.get('source', '')} ({a.get('date', '')})\n"
                f"   {a.get('snippet', '')}\n"
                f"   Источник: {a.get('link', '—')}"
            )

    lines.extend(
        [
            "",
            "## Финансовые показатели",
            f"- Текущая цена: {fin.get('current_price')} {fin.get('currency', '')}",
            f"- Рыночная капитализация: {fin.get('market_cap')}",
            f"- Сектор / отрасль: {fin.get('sector')} / {fin.get('industry')}",
            f"- 52W min / max: {fin.get('fifty_two_week_low')} / {fin.get('fifty_two_week_high')}",
            f"- Beta: {fin.get('beta')}",
            "",
            "## Мультипликаторы",
            f"- P/E: {fin.get('pe_ratio')}",
            f"- P/B: {fin.get('pb_ratio')}",
            f"- ROE: {fin.get('roe_pct')}%",
            f"- Дивидендная доходность: {fin.get('dividend_yield_pct')}%",
            f"- Рост выручки (3Y CAGR): {fin.get('revenue_growth_3y_cagr_pct')}%",
            f"- Маржа прибыли: {fin.get('profit_margin_pct')}%",
            f"- Долг/капитал: {fin.get('debt_to_equity')}",
            "",
            "## Риски",
            "- Волатильность: оцените beta и диапазон 52 недель.",
            "- Макро- и отраслевые риски: см. новостной фон.",
            "- Рыночный риск: данные отражают прошлую отчётность, не гарантируют будущих результатов.",
            "",
            "## Итог",
            "Сводка составлена автоматически из открытых данных (yfinance / новости). "
            "Выводы носят описательный характер.",
            "",
            "**Это не инвестиционная рекомендация. Информация носит аналитический характер.**",
            "",
            "_Режим без LLM: добавьте бесплатный GROQ_API_KEY в .streamlit/secrets.toml "
            "(https://console.groq.com) для отчёта с ReAct-агентом._",
        ]
    )
    return "\n".join(lines)


def create_investment_agent(llm: BaseChatModel) -> AgentExecutor:
    """LangChain ReAct agent with financial + news tools."""
    tools = [get_stock_financials, search_news]
    prompt = PromptTemplate.from_template(REACT_TEMPLATE)
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
        return_intermediate_steps=True,
    )


def run_analysis(
    ticker: str,
    status_callback: Any = None,
) -> dict[str, Any]:
    """
    Full analysis pipeline.
    Returns dict: report, thoughts, financials, news, mode.
    """
    ticker = ticker.strip()
    if not ticker:
        return {"error": "Введите тикер компании."}

    if status_callback:
        status_callback("Загружаю финансы и ищу новости...")

    financials, news = prefetch_parallel(ticker.upper())

    llm = build_llm()
    thoughts: list[str] = [
        "Параллельная загрузка: get_stock_financials + search_news выполнены.",
    ]

    if llm is None:
        if status_callback:
            status_callback("Формирую отчёт (шаблон, без LLM)...")
        report = _template_report(ticker, financials, news)
        return {
            "report": report,
            "thoughts": thoughts + ["LLM не настроен — использован шаблонный отчёт."],
            "financials": financials,
            "news": news,
            "mode": "template",
        }

    if status_callback:
        status_callback("Формирую отчёт (ReAct-агент)...")

    executor = create_investment_agent(llm)
    logger = AgentThoughtLogger()
    if status_callback:
        logger.set_status_callback(status_callback)

    user_input = (
        f"Проанализируй компанию с тикером {ticker.upper()}. "
        f"Обязательно используй инструменты get_stock_financials и search_news. "
        f"Контекст (для сверки): FINANCIALS={financials[:2000]}... NEWS={news[:2000]}..."
    )

    try:
        result = executor.invoke(
            {"input": user_input},
            config={"callbacks": [logger]},
        )
        report = result.get("output", "")
        for action, observation in result.get("intermediate_steps", []):
            thoughts.append(f"Action: {action.tool} | Obs: {str(observation)[:200]}...")
        thoughts.extend(logger.steps)
        return {
            "report": report,
            "thoughts": thoughts,
            "financials": financials,
            "news": news,
            "mode": "react",
        }
    except Exception as e:
        thoughts.append(f"Ошибка агента: {e}")
        report = _template_report(ticker, financials, news)
        thoughts.append("Использован резервный шаблонный отчёт.")
        return {
            "report": report,
            "thoughts": thoughts,
            "financials": financials,
            "news": news,
            "mode": "template_fallback",
            "error": str(e),
        }
