"""
Investment Idea Analyzer — Streamlit UI (redesigned dark theme).
 
Запуск из папки investment_agent:
    streamlit run app.py
"""
 
from __future__ import annotations
 
import io
import json
 
from dotenv import load_dotenv
 
load_dotenv()
from datetime import datetime, timedelta
 
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import streamlit as st
import yfinance as yf
 
from agent import is_groq_configured, run_analysis
from tools import _resolve_ticker
 
# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InvestAgent · AI Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ── Global CSS ─────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');
 
/* ── Reset & root ── */
:root {
  --bg:       #0A0C0F;
  --surface:  #111318;
  --surface2: #181C22;
  --border:   #1E2330;
  --border2:  #2A3040;
  --accent:   #4EFFA3;
  --accent2:  #7B8CFF;
  --accent3:  #FFB347;
  --text:     #E8EAF0;
  --muted:    #5A6175;
  --danger:   #FF5757;
}
 
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Syne', sans-serif !important;
}
 
/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.stDeployButton { display: none; }
 
/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
 
/* ── Main content padding ── */
[data-testid="stMain"] > div { padding-top: 1.5rem; }
.block-container { padding: 1.5rem 2rem 3rem 2rem !important; max-width: 100% !important; }
 
/* ── Typography ── */
h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.03em; }
.stMarkdown p, .stMarkdown li { font-family: 'Syne', sans-serif !important; }
 
/* ── Input ── */
[data-testid="stTextInput"] input {
  background: var(--surface) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  letter-spacing: 0.5px !important;
  padding: 14px 18px !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(78,255,163,0.15) !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--muted) !important; }
 
/* ── Primary button ── */
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  color: #0A0C0F !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.5px !important;
  border: none !important;
  border-radius: 10px !important;
  padding: 14px 28px !important;
  transition: opacity .2s !important;
}
.stButton > button[kind="primary"]:hover { opacity: 0.88 !important; }
 
/* ── Secondary / default button ── */
.stButton > button:not([kind="primary"]) {
  background: var(--surface2) !important;
  color: var(--muted) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 11px !important;
}
 
/* ── Metric cards ── */
[data-testid="stMetric"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  padding: 14px !important;
}
[data-testid="stMetricLabel"] {
  font-family: 'DM Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 0.8px !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Syne', sans-serif !important;
  font-size: 22px !important;
  font-weight: 700 !important;
  color: var(--text) !important;
  letter-spacing: -0.5px !important;
}
 
/* ── Alerts / Status ── */
[data-testid="stAlert"] {
  border-radius: 8px !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 12px !important;
}
div[data-baseweb="notification"][kind="info"] {
  background: rgba(123,140,255,0.08) !important;
  border: 1px solid rgba(123,140,255,0.2) !important;
  color: var(--accent2) !important;
}
div[data-baseweb="notification"][kind="positive"] {
  background: rgba(78,255,163,0.06) !important;
  border: 1px solid rgba(78,255,163,0.2) !important;
}
 
/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
  font-family: 'DM Mono', monospace !important;
  font-size: 11px !important;
  color: var(--muted) !important;
  letter-spacing: 0.5px !important;
}
 
/* ── Spinner ── */
[data-testid="stSpinner"] { color: var(--accent) !important; }
 
/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }
</style>
"""
 
# ── Sidebar HTML components ────────────────────────────────────────────────────
def sidebar_logo() -> str:
    return """
<div style="display:flex;align-items:center;gap:10px;
            border-bottom:1px solid #1E2330;padding-bottom:20px;margin-bottom:4px;">
  <div style="width:36px;height:36px;border-radius:10px;
              background:linear-gradient(135deg,#4EFFA3,#7B8CFF);
              display:flex;align-items:center;justify-content:center;
              font-size:17px;font-weight:800;color:#0A0C0F;letter-spacing:-1px;
              font-family:'Syne',sans-serif;">$</div>
  <div>
    <div style="font-size:15px;font-weight:700;letter-spacing:0.5px;
                font-family:'Syne',sans-serif;color:#E8EAF0;">InvestAgent</div>
    <div style="font-size:10px;color:#5A6175;font-family:'DM Mono',monospace;margin-top:1px;">
      AI · Research · v1.0</div>
  </div>
</div>
"""
 
def sidebar_status(groq_ok: bool) -> str:
    groq_dot = '<div style="width:6px;height:6px;border-radius:50%;background:#4EFFA3;box-shadow:0 0 6px #4EFFA3;flex-shrink:0;"></div>'
    serp_dot = '<div style="width:6px;height:6px;border-radius:50%;background:#FFB347;box-shadow:0 0 6px #FFB347;flex-shrink:0;"></div>'
    groq_label = "Groq API: подключён" if groq_ok else "Groq API: не задан"
    groq_dot_html = groq_dot if groq_ok else serp_dot
    return f"""
<div style="background:#181C22;border:1px solid #1E2330;border-radius:10px;padding:14px;margin-bottom:4px;">
  <div style="font-size:10px;color:#5A6175;font-family:'DM Mono',monospace;
              letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Соединение</div>
  <div style="display:flex;align-items:center;gap:8px;font-size:12px;
              color:#E8EAF0;margin-bottom:8px;font-family:'Syne',sans-serif;">
    {groq_dot_html} {groq_label}
  </div>
  <div style="display:flex;align-items:center;gap:8px;font-size:12px;
              color:#E8EAF0;font-family:'Syne',sans-serif;">
    {serp_dot} SerpAPI: не задан
  </div>
</div>
"""
 
def sidebar_keys() -> str:
    return """
<div style="background:#181C22;border:1px solid #1E2330;border-radius:10px;padding:14px;margin-bottom:4px;">
  <div style="font-size:10px;color:#5A6175;font-family:'DM Mono',monospace;
              letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Конфигурация</div>
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding:6px 0;border-bottom:1px solid #1E2330;">
    <span style="font-size:11px;font-family:'DM Mono',monospace;color:#5A6175;">GROQ_API_KEY</span>
    <span style="font-size:10px;color:#4EFFA3;font-family:'DM Mono',monospace;">gsk_••••••</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding:6px 0;border-bottom:1px solid #1E2330;">
    <span style="font-size:11px;font-family:'DM Mono',monospace;color:#5A6175;">SERPAPI_KEY</span>
    <span style="font-size:10px;color:#5A6175;font-family:'DM Mono',monospace;">не задан</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;">
    <span style="font-size:11px;font-family:'DM Mono',monospace;color:#5A6175;">OPENAI_KEY</span>
    <span style="font-size:10px;color:#5A6175;font-family:'DM Mono',monospace;">не задан</span>
  </div>
</div>
"""
 
def sidebar_footer() -> str:
    return """
<div style="font-size:11px;color:#5A6175;font-family:'DM Mono',monospace;
            line-height:2;border-top:1px solid #1E2330;padding-top:16px;margin-top:4px;">
  <div>Новости: yfinance (бесплатно)</div>
  <div>Агент: LangChain ReAct</div>
  <div style="margin-top:8px;color:rgba(90,97,117,0.5);font-size:10px;">
    Python · Streamlit · LangChain</div>
</div>
"""
 
# ── Reusable HTML helpers ──────────────────────────────────────────────────────
def section_header(title: str, badge: str = "") -> str:
    badge_html = (
        f'<div style="font-size:10px;font-family:\'DM Mono\',monospace;'
        f'background:rgba(78,255,163,0.1);color:#4EFFA3;'
        f'border:1px solid rgba(78,255,163,0.2);'
        f'padding:3px 10px;border-radius:20px;">{badge}</div>'
        if badge else ""
    )
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
  <div style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;
              color:#5A6175;font-family:'DM Mono',monospace;">{title}</div>
  {badge_html}
</div>
"""
 
def hero_html() -> str:
    return """
<div style="display:flex;flex-direction:column;gap:6px;margin-bottom:8px;">
  <div style="font-size:32px;font-weight:800;letter-spacing:-1.5px;line-height:1.05;
              font-family:'Syne',sans-serif;color:#E8EAF0;">
    Investment<br>
    <span style="background:linear-gradient(90deg,#4EFFA3,#7B8CFF);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text;">AI Analyzer</span>
  </div>
  <div style="font-size:13px;color:#5A6175;max-width:520px;line-height:1.7;
              font-family:'Syne',sans-serif;margin-top:4px;">
    Введите тикер или название компании — агент соберёт новости,
    финансовые показатели и сформирует структурированный аналитический отчёт.
  </div>
</div>
"""
 
def disclaimer_html() -> str:
    return """
<div style="border:1px solid rgba(255,87,87,0.25);border-left:3px solid #FF5757;
            background:rgba(255,87,87,0.04);border-radius:0 8px 8px 0;
            padding:10px 14px;font-size:11px;color:rgba(255,87,87,0.8);
            line-height:1.6;font-family:'DM Mono',monospace;margin-bottom:4px;">
  ⚠ Дисклеймер: данное приложение — аналитический инструмент для образовательных
  целей. Оно <strong>не является</strong> инвестиционной рекомендацией и не
  предлагает совершить сделку.
</div>
"""
 
def chart_wrapper(content_html: str, badge: str) -> str:
    return f"""
<div style="background:#111318;border:1px solid #1E2330;border-radius:12px;
            padding:20px;margin-bottom:4px;">
  {section_header("Динамика цены · 1 год", badge)}
  {content_html}
</div>
"""
 
def report_section_html(tabs: list[str], active: int, content: str) -> str:
    tabs_html = "".join(
        f'<div style="font-size:11px;font-family:\'DM Mono\',monospace;letter-spacing:0.5px;'
        f'padding:5px 14px;border-radius:6px;cursor:pointer;'
        + (
            'background:rgba(78,255,163,0.1);color:#4EFFA3;border:1px solid rgba(78,255,163,0.2);'
            if i == active else
            'color:#5A6175;border:1px solid transparent;'
        )
        + f'">{t}</div>'
        for i, t in enumerate(tabs)
    )
    return f"""
<div style="background:#111318;border:1px solid #1E2330;border-radius:12px;
            padding:20px;margin-top:8px;">
  <div style="display:flex;gap:4px;margin-bottom:16px;
              border-bottom:1px solid #1E2330;padding-bottom:12px;flex-wrap:wrap;">
    {tabs_html}
  </div>
  <div style="font-size:13px;line-height:1.8;color:rgba(232,234,240,0.85);
              font-family:'Syne',sans-serif;">
    {content}
  </div>
</div>
"""
 
def report_h(text: str) -> str:
    return (
        f'<div style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;'
        f'color:#4EFFA3;font-family:\'DM Mono\',monospace;'
        f'margin:16px 0 8px;border-left:2px solid #4EFFA3;padding-left:10px;">'
        f'{text}</div>'
    )
 
def report_row(key: str, val: str, color: str = "#E8EAF0") -> str:
    return (
        f'<div style="display:flex;align-items:baseline;gap:8px;padding:5px 0;'
        f'border-bottom:1px solid #1E2330;font-size:12px;">'
        f'<span style="color:#5A6175;font-family:\'DM Mono\',monospace;'
        f'flex-shrink:0;width:190px;min-width:190px;">{key}</span>'
        f'<span style="color:{color};">{val}</span></div>'
    )
 
def footer_disclaimer_html() -> str:
    return """
<div style="text-align:center;font-size:11px;color:#FF5757;
            font-family:'DM Mono',monospace;opacity:.7;
            border-top:1px solid #1E2330;padding-top:16px;margin-top:8px;">
  Это не инвестиционная рекомендация. Информация носит аналитический характер.
</div>
"""
 
# ── Chart ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(ticker: str) -> pd.DataFrame | None:
    sym, err = _resolve_ticker(ticker)
    if err:
        return None
    try:
        t = yf.Ticker(sym)
        end = datetime.now()
        start = end - timedelta(days=365)
        hist = t.history(start=start, end=end, auto_adjust=True)
        return hist if hist is not None and not hist.empty else None
    except Exception:
        return None
 
 
def build_price_chart(hist: pd.DataFrame, title: str) -> bytes:
    fig, ax = plt.subplots(figsize=(11, 3.2))
    fig.patch.set_facecolor("#111318")
    ax.set_facecolor("#111318")
 
    closes = hist["Close"]
    xs = hist.index
 
    # Fill gradient-like area
    ax.fill_between(xs, closes, alpha=0.12, color="#4EFFA3", linewidth=0)
    ax.plot(xs, closes, color="#4EFFA3", linewidth=1.6, zorder=3)
 
    # Style
    ax.set_title(title, fontsize=11, color="#5A6175", fontfamily="monospace",
                 loc="left", pad=8)
    ax.tick_params(colors="#5A6175", labelsize=9)
    ax.spines[:].set_color("#1E2330")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_tick_params(color="#1E2330")
    ax.xaxis.set_tick_params(color="#1E2330")
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_color("#5A6175")
        label.set_fontfamily("monospace")
    ax.grid(True, color="#1E2330", linewidth=0.7, linestyle="--", alpha=0.6)
 
    fig.tight_layout(pad=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
 
 
# ── Metrics card ──────────────────────────────────────────────────────────────
def render_financials_card(financials_raw: str) -> None:
    try:
        data = json.loads(financials_raw)
    except json.JSONDecodeError:
        st.warning("Не удалось разобрать финансовые данные.")
        return
    if data.get("error"):
        st.error(data["error"])
        return
 
    def _fmt(v, suffix=""):
        return f"{v}{suffix}" if v is not None else "—"
 
    cap = data.get("market_cap")
    cap_str = f"{cap / 1e9:.2f}B" if cap else "—"
 
    metrics = [
        ("Цена",         f"{_fmt(data.get('current_price'))} {data.get('currency', '')}".strip(), "green"),
        ("P/E",          _fmt(data.get("pe_ratio")),  "blue"),
        ("Капитализация", cap_str,                     "text"),
        ("ROE",          _fmt(data.get("roe_pct"), "%"), "amber"),
        ("P/B",          _fmt(data.get("pb_ratio")), "blue"),
        ("Дивиденды",    _fmt(data.get("dividend_yield_pct"), "%"), "text"),
        ("Выручка 3Y",   _fmt(data.get("revenue_growth_3y_cagr_pct"), "%"), "green"),
        ("Долг/капитал", _fmt(data.get("debt_to_equity")), "text"),
    ]
 
    color_map = {
        "green": "#4EFFA3",
        "blue":  "#7B8CFF",
        "amber": "#FFB347",
        "text":  "#E8EAF0",
    }
 
    subs = ["USD", "trailing", "USD", "trailing",
            "ratio", "yield", "CAGR", "D/E ratio"]
 
    cards_html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:4px;">'
    for (label, val, clr), sub in zip(metrics, subs):
        cards_html += f"""
<div style="background:#111318;border:1px solid #1E2330;border-radius:10px;padding:14px;">
  <div style="font-size:10px;color:#5A6175;font-family:'DM Mono',monospace;
              letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px;">{label}</div>
  <div style="font-size:22px;font-weight:700;letter-spacing:-0.5px;
              color:{color_map[clr]};font-family:'Syne',sans-serif;">{val}</div>
  <div style="font-size:10px;color:#5A6175;margin-top:2px;
              font-family:'DM Mono',monospace;">{sub}</div>
</div>"""
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
 
 
# ── Report tabs ───────────────────────────────────────────────────────────────
def render_report_tabs(report_md: str, news_raw: str, financials_raw: str) -> None:
    TABS = ["Новостной фон", "Финансы", "Мультипликаторы", "Риски", "Итог"]
 
    # Streamlit native tabs with custom CSS overlay
    st.markdown("""
<style>
[data-testid="stTabs"] [role="tablist"] {
  background: transparent !important;
  gap: 4px !important;
  border-bottom: 1px solid #1E2330 !important;
  padding-bottom: 2px !important;
}
[data-testid="stTabs"] button[role="tab"] {
  font-family: 'DM Mono', monospace !important;
  font-size: 11px !important;
  letter-spacing: 0.5px !important;
  color: #5A6175 !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: 6px !important;
  padding: 5px 14px !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  color: #4EFFA3 !important;
  background: rgba(78,255,163,0.1) !important;
  border-color: rgba(78,255,163,0.2) !important;
}
[data-testid="stTabs"] [role="tabpanel"] {
  background: #111318 !important;
  border: 1px solid #1E2330 !important;
  border-radius: 0 10px 10px 10px !important;
  padding: 20px !important;
}
</style>
""", unsafe_allow_html=True)
 
    tabs = st.tabs(TABS)
 
    # ── Tab 0: News ──
    with tabs[0]:
        try:
            news = json.loads(news_raw)
            articles = news.get("articles", [])
        except Exception:
            articles = []
 
        if articles:
            rows = ""
            for a in articles:
                link = a.get("link", "#")
                title = a.get("title", "Без заголовка")
                source = a.get("source", "")
                date = a.get("date", "")
                key_str = f"{source} · {date}" if source else date
                rows += report_row(
                    key_str,
                    f'<a href="{link}" target="_blank" style="color:#E8EAF0;text-decoration:none;'
                    f'border-bottom:1px solid #2A3040;">{title}</a>',
                )
            st.markdown(report_h("Последние новости") + rows, unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="color:#5A6175;font-family:\'DM Mono\',monospace;font-size:12px;">'
                "Новости не найдены.</p>",
                unsafe_allow_html=True,
            )
 
    # ── Tab 1: Financials (raw report section) ──
    with tabs[1]:
        _render_report_section(report_md, "## Финансовые показатели")
 
    # ── Tab 2: Multiples ──
    with tabs[2]:
        _render_report_section(report_md, "## Мультипликаторы")
 
    # ── Tab 3: Risks ──
    with tabs[3]:
        _render_report_section(report_md, "## Риски")
 
    # ── Tab 4: Summary ──
    with tabs[4]:
        _render_report_section(report_md, "## Итог")
 
 
def _render_report_section(report_md: str, heading: str) -> None:
    """Extract and render one ## section from the markdown report."""
    lines = report_md.splitlines()
    in_section = False
    section_lines = []
    for line in lines:
        if line.strip().startswith("## "):
            if in_section:
                break
            if heading.lower() in line.lower():
                in_section = True
                continue
        if in_section:
            section_lines.append(line)
 
    content = "\n".join(section_lines).strip()
    if content:
        st.markdown(
            f'<div style="font-size:13px;line-height:1.8;color:rgba(232,234,240,0.85);'
            f'font-family:\'Syne\',sans-serif;">{_md_to_html(content)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color:#5A6175;font-family:\'DM Mono\',monospace;font-size:12px;">'
            "Данные в разделе отсутствуют.</p>",
            unsafe_allow_html=True,
        )
 
 
def _md_to_html(text: str) -> str:
    """Minimal Markdown → HTML (bold, lists, newlines)."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    lines = text.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            out.append(
                f'<div style="padding:4px 0;border-bottom:1px solid #1E2330;font-size:12px;">'
                f'<span style="color:#5A6175;margin-right:8px;">—</span>{stripped[2:]}</div>'
            )
        elif stripped:
            out.append(f"<p style='margin:4px 0;'>{stripped}</p>")
    return "\n".join(out)
 
 
# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    # Inject global CSS
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
 
    # ── Sidebar ──
    with st.sidebar:
        st.markdown(sidebar_logo(), unsafe_allow_html=True)
        st.markdown(sidebar_status(is_groq_configured()), unsafe_allow_html=True)
        st.markdown(sidebar_keys(), unsafe_allow_html=True)
        st.markdown(sidebar_footer(), unsafe_allow_html=True)
 
    # ── Hero ──
    st.markdown(hero_html(), unsafe_allow_html=True)
    st.markdown(disclaimer_html(), unsafe_allow_html=True)
 
    # ── Search row ──
    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        ticker_input = st.text_input(
            label="ticker",
            placeholder="NVDA, Apple, TSLA...",
            label_visibility="collapsed",
            key="ticker_input",
        )
    with col_btn:
        analyze = st.button("АНАЛИЗИРОВАТЬ →", type="primary", use_container_width=True)
 
    # ── Analysis ──
    if analyze:
        if not ticker_input.strip():
            st.markdown(
                '<div style="color:#FF5757;font-family:\'DM Mono\',monospace;font-size:12px;'
                'padding:8px 0;">⚠ Введите тикер или название компании.</div>',
                unsafe_allow_html=True,
            )
            return
 
        status_box = st.empty()
 
        def set_status(msg: str) -> None:
            status_box.markdown(
                f'<div style="background:rgba(123,140,255,0.08);border:1px solid rgba(123,140,255,0.2);'
                f'border-radius:8px;padding:10px 14px;font-family:\'DM Mono\',monospace;'
                f'font-size:12px;color:#7B8CFF;">⏳ {msg}</div>',
                unsafe_allow_html=True,
            )
 
        set_status("Загружаю финансы и ищу новости...")
 
        with st.spinner("Агент работает..."):
            result = run_analysis(ticker_input, status_callback=set_status)
 
        status_box.empty()
 
        if result.get("error") and "report" not in result:
            st.error(result["error"])
            return
        if result.get("error"):
            st.markdown(
                f'<div style="color:#FFB347;font-family:\'DM Mono\',monospace;font-size:11px;">'
                f'⚠ {result["error"]}</div>',
                unsafe_allow_html=True,
            )
 
        sym, _ = _resolve_ticker(ticker_input)
        display_ticker = sym or ticker_input.upper()
 
        # Success badge
        mode = result.get("mode", "unknown")
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:8px;'
            f'background:rgba(78,255,163,0.06);border:1px solid rgba(78,255,163,0.2);'
            f'border-radius:8px;padding:6px 14px;font-size:11px;'
            f'font-family:\'DM Mono\',monospace;color:#4EFFA3;margin-bottom:8px;">'
            f'✓ Анализ завершён · {mode}</div>',
            unsafe_allow_html=True,
        )
 
        # ── Price chart ──
        hist = fetch_price_history(ticker_input)
        if hist is not None:
            name = display_ticker
            try:
                info = json.loads(result.get("financials", "{}"))
                name = info.get("company_name", display_ticker)
            except Exception:
                pass
 
            price_badge = display_ticker
            try:
                fin_d = json.loads(result.get("financials", "{}"))
                p = fin_d.get("current_price")
                if p:
                    price_badge = f"{display_ticker} · ${p:,.2f}"
            except Exception:
                pass
 
            img_bytes = build_price_chart(hist, f"{name}  ·  1Y")
            st.markdown(
                f'<div style="background:#111318;border:1px solid #1E2330;'
                f'border-radius:12px;padding:20px;">'
                f'{section_header("Динамика цены · 1 год", price_badge)}'
                f'</div>',
                unsafe_allow_html=True,
            )
            # Re-render with image inside a styled container
            with st.container():
                st.markdown(
                    '<div style="background:#111318;border:1px solid #1E2330;'
                    'border-radius:12px;padding:4px 20px 16px 20px;margin-top:-16px;">',
                    unsafe_allow_html=True,
                )
                st.image(img_bytes, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="color:#5A6175;font-family:\'DM Mono\',monospace;font-size:12px;">'
                "График цены недоступен для данного тикера.</div>",
                unsafe_allow_html=True,
            )
 
        # ── Metric cards ──
        st.markdown(
            '<div style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;'
            'color:#5A6175;font-family:\'DM Mono\',monospace;margin:16px 0 10px;">Ключевые метрики</div>',
            unsafe_allow_html=True,
        )
        render_financials_card(result.get("financials", "{}"))
 
        # ── Report tabs ──
        st.markdown(
            '<div style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;'
            'color:#5A6175;font-family:\'DM Mono\',monospace;margin:16px 0 10px;">Аналитический отчёт</div>',
            unsafe_allow_html=True,
        )
        render_report_tabs(
            result.get("report", ""),
            result.get("news", "{}"),
            result.get("financials", "{}"),
        )
 
        # ── Agent thoughts ──
        thoughts = result.get("thoughts", [])
        with st.expander(f"▶ Ход мыслей агента · {len(thoughts)} шагов"):
            for step in thoughts:
                st.markdown(
                    f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;'
                    f'color:#5A6175;padding:4px 0;border-bottom:1px solid #1E2330;">'
                    f'{step}</div>',
                    unsafe_allow_html=True,
                )
 
        # ── News sources ──
        with st.expander("▶ Источники новостей"):
            try:
                news = json.loads(result.get("news", "{}"))
                for a in news.get("articles", []):
                    st.markdown(
                        f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;'
                        f'color:#5A6175;padding:4px 0;border-bottom:1px solid #1E2330;">'
                        f'<a href="{a.get("link","#")}" target="_blank" '
                        f'style="color:#4EFFA3;">{a.get("title","Без заголовка")}</a>'
                        f' — {a.get("source","")} ({a.get("date","")})</div>',
                        unsafe_allow_html=True,
                    )
                if not news.get("articles"):
                    st.markdown(
                        f'<span style="color:#5A6175;font-size:11px;'
                        f'font-family:\'DM Mono\',monospace;">'
                        f'{news.get("message","Нет новостей")}</span>',
                        unsafe_allow_html=True,
                    )
            except Exception:
                st.text(result.get("news", ""))
 
        st.markdown(footer_disclaimer_html(), unsafe_allow_html=True)
 
 
if __name__ == "__main__":
    main()