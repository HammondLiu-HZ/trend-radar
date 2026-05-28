"""Trend Radar — realtime Hacker News hot list (MVP)."""
from __future__ import annotations

from datetime import datetime, timezone

import re
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st
from wordcloud import STOPWORDS, WordCloud

from radar import storage, trends
from radar.sources import fetch_top_stories

st.set_page_config(page_title="Trend Radar", page_icon="📡", layout="wide")


@st.cache_data(ttl=300, show_spinner="抓取 Hacker News 实时热榜…")
def load_data(limit: int):
    current = pd.DataFrame(fetch_top_stories(limit=limit))
    if current.empty:
        return current, pd.DataFrame()
    current["published"] = pd.to_datetime(current["time"], unit="s", utc=True)
    previous = storage.load_previous_snapshot()
    storage.save_snapshot(current)
    return current, previous


def humanize_age(ts: pd.Timestamp) -> str:
    seconds = (datetime.now(timezone.utc) - ts.to_pydatetime()).total_seconds()
    if seconds < 3600:
        return f"{int(seconds // 60)} 分钟前"
    if seconds < 86400:
        return f"{int(seconds // 3600)} 小时前"
    return f"{int(seconds // 86400)} 天前"


_EXTRA_STOP = {"show", "ask", "hn", "new", "use", "using", "via", "way", "vs", "day", "make", "get"}


@st.cache_data(ttl=300)
def build_wordcloud(titles: tuple):
    words = re.findall(r"[a-z][a-z0-9+#.]{2,}", " ".join(titles).lower())
    stop = {w.lower() for w in STOPWORDS} | _EXTRA_STOP
    freq = Counter(w for w in words if w not in stop)
    if not freq:
        return None
    wc = WordCloud(
        width=600,
        height=360,
        background_color="#0e1117",
        colormap="Oranges",
        prefer_horizontal=0.9,
    ).generate_from_frequencies(dict(freq))
    return wc.to_array()


# ---- Sidebar ----
st.sidebar.title("📡 Trend Radar")
st.sidebar.caption("实时热点雷达 · Hacker News")
limit = st.sidebar.slider("抓取条数", 10, 100, 30, step=10)
if st.sidebar.button("🔄 立即刷新", use_container_width=True):
    load_data.clear()

# ---- Main ----
st.title("📡 Hacker News 实时热榜")

df, previous = load_data(limit)
if df.empty:
    st.warning("暂时没抓到数据，请稍后重试。")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("条目数", len(df))
c2.metric("最高分", int(df["score"].max()))
c3.metric("总评论数", int(df["comments"].sum()))
st.caption(f"更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.subheader("🔥 窜升榜")
risers = trends.compute_risers(df, previous)
if risers.empty:
    st.info(
        f"正在积累历史快照（已有 {storage.snapshot_count()} 次）。"
        "窜升榜需要至少两次抓取，过几分钟刷新即可看到。"
    )
else:
    rise_view = risers[["status", "title", "score", "score_delta", "comments"]].copy()
    rise_view["score_delta"] = rise_view["score_delta"].astype(int)
    st.dataframe(
        rise_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "status": st.column_config.TextColumn("状态", width="small"),
            "title": st.column_config.TextColumn("标题", width="large"),
            "score": st.column_config.NumberColumn("当前分"),
            "score_delta": st.column_config.NumberColumn("↑ 涨分"),
            "comments": st.column_config.NumberColumn("评论"),
        },
    )

st.subheader("Top 10 热度")
top10 = df.nsmallest(10, "rank").copy()
top10["label"] = top10["title"].str.slice(0, 45)
fig = px.bar(
    top10.sort_values("score"),
    x="score",
    y="label",
    orientation="h",
    color="score",
    color_continuous_scale="Oranges",
    text="score",
)
fig.update_layout(height=420, yaxis_title="", xaxis_title="分数", coloraxis_showscale=False)
st.plotly_chart(fig, use_container_width=True)

st.subheader("📊 洞察")
col_a, col_b = st.columns(2)
with col_a:
    st.caption("标题关键词云")
    cloud = build_wordcloud(tuple(df["title"].tolist()))
    if cloud is not None:
        st.image(cloud, use_container_width=True)
with col_b:
    st.caption("分数 vs 评论")
    fig_sc = px.scatter(
        df,
        x="comments",
        y="score",
        size="score",
        hover_name="title",
        color="score",
        color_continuous_scale="Oranges",
    )
    fig_sc.update_layout(height=360, coloraxis_showscale=False, xaxis_title="评论数", yaxis_title="分数")
    st.plotly_chart(fig_sc, use_container_width=True)

st.caption("发布时段分布（UTC 小时）")
by_hour = df["published"].dt.hour.value_counts().sort_index()
fig_h = px.bar(x=by_hour.index, y=by_hour.values, color=by_hour.values, color_continuous_scale="Oranges")
fig_h.update_layout(height=240, coloraxis_showscale=False, xaxis_title="UTC 小时", yaxis_title="条数")
st.plotly_chart(fig_h, use_container_width=True)

st.subheader("完整热榜")
st.caption("点击任意一行查看详情与原文链接")
view = df.copy()
view["发布"] = view["published"].apply(humanize_age)
table = view[["rank", "title", "score", "comments", "by", "发布", "url"]]
event = st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "rank": st.column_config.NumberColumn("#", width="small"),
        "title": st.column_config.TextColumn("标题", width="large"),
        "score": st.column_config.NumberColumn("分数"),
        "comments": st.column_config.NumberColumn("评论"),
        "by": st.column_config.TextColumn("作者"),
        "url": st.column_config.LinkColumn("链接", display_text="打开"),
    },
)
selected = event.selection["rows"] if event.selection else []
if selected:
    r = df.iloc[selected[0]]
    with st.container(border=True):
        st.markdown(f"#### {r['title']}")
        st.markdown(f"👤 {r['by']} · 🔺 {int(r['score'])} 分 · 💬 {int(r['comments'])} 评论")
        st.markdown(f"[🔗 阅读原文]({r['url']}) · [💬 HN 讨论]({r['hn_url']})")
