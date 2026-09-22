"""
推荐算法服务 v2.0

相比 v1 的核心升级：
─────────────────────────────────────────────────────────
 1. 相关文章推荐：使用 TF-IDF 向量化 + 余弦相似度（基于 title/excerpt/content）
    · 标签匹配权重 0.30（含 Jaccard 系数）
    · 分类匹配权重 0.20
    · TF-IDF 文本相似度 0.30
    · 时间衰减（指数 + 对数双保险）0.12
    · 互动热度（log-normalized views/likes/comments）0.08

 2. 首页推荐：多臂老虎机 ε-greedy 风格
    · 10% 冷启动探索（随机 + 最新）
    · 90% 利用（综合 UCB 得分：热度 × 标签偏好 × 时间新鲜度）

 3. 搜索召回增强（被 blog.search_posts 复用）
    · BM25-Okapi 风格的词频权重
    · 字段级加权：title × 3.0 + excerpt × 1.5 + tags × 2.0 + content × 1.0
    · 中文 / CJK 走字符 2-gram；英文走 whitespace token
"""

from __future__ import annotations

import logging
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.models.blog import Comment, Post, PostViewHistory, post_likes, post_tags
from backend.services.cache_service import CacheService, get_cache_service
from backend.utils.compat import UTC

logger = logging.getLogger(__name__)

# ──────────────────────────── 缓存 TTL ────────────────────────────
RECOMMENDATION_TTL = 60 * 5  # 首页推荐：5 分钟
SIMILAR_POSTS_TTL = 60 * 30  # 相似文章：30 分钟（变化小）
SEARCH_TTL = 60 * 3  # 搜索查询缓存：3 分钟
HOT_RANKING_TTL = 60 * 10  # 热榜：10 分钟

# ──────────────────────────── 算法权重 ────────────────────────────
SIMILAR_WEIGHTS = {
    "tags": 0.30,  # 标签 Jaccard
    "category": 0.20,  # 分类完全匹配
    "tfidf": 0.30,  # 文本余弦
    "time": 0.12,  # 时间衰减
    "heat": 0.08,  # 互动热度
}

DECAY_LAMBDA = 0.06  # 指数衰减系数（天）：≈15 天到 40%
TIME_HALF_LIFE_DAYS = 30.0

BM25_K1 = 1.5  # BM25 Okapi 词频饱和参数
BM25_B = 0.75  # 文档长度归一化权重
AVG_DOC_LEN_ESTIMATE = 1200  # 预估平均文档长度（字）
BM25_FIELD_WEIGHTS: list[tuple[str, float]] = [
    ("title", 3.0),
    ("tags", 2.0),
    ("excerpt", 1.5),
    ("content", 1.0),
]
EXPLORE_EPSILON = 0.10  # 推荐冷启动探索比例

CJK_PATTERN = re.compile(r"[\u3400-\u9FFF\uF900-\uFAFF\u3040-\u30FF\uAC00-\uD7AF]")
WORD_PATTERN = re.compile(r"[A-Za-z0-9\u00C0-\u024F]+")


# ──────────────────────────── 工具函数 ────────────────────────────


def normalize_text(text: str | None) -> str:
    """统一去 HTML/Markdown 噪音、去重空格、NFKC 归一化。"""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text).lower()
    s = re.sub(r"```[\s\S]*?```", " ", s)  # code fence
    s = re.sub(r"`[^`]*`", " ", s)  # inline code
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)  # md image
    s = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", s)  # md link
    s = re.sub(r"<[^>]+>", " ", s)  # html tags
    s = re.sub(r"[#>*_~\-+|`]", " ", s)  # md punctuation
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def tokenize(text: str) -> list[str]:
    """双语种 tokenizer：CJK 走 char 2-gram，英文走单词。"""
    if not text:
        return []
    tokens: list[str] = []
    # 英文单词
    for m in WORD_PATTERN.finditer(text):
        w = m.group(0)
        if len(w) >= 2:
            tokens.append(w)
    # CJK 2-gram
    cjk_chars: list[str] = []
    for ch in text:
        if CJK_PATTERN.match(ch):
            cjk_chars.append(ch)
    for i in range(len(cjk_chars) - 1):
        tokens.append(cjk_chars[i] + cjk_chars[i + 1])
    return tokens


def build_tf(tokens: list[str]) -> Counter[str]:
    """词频计数（term frequency）。"""
    return Counter(tokens)


def compute_cosine_similarity(
    tf_a: Counter[str], tf_b: Counter[str], idf: dict[str, float]
) -> float:
    """基于共享 IDF 表计算两个 TF 向量的 TF-IDF 余弦相似度。"""
    if not tf_a or not tf_b:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    # 只遍历较小的一侧
    small, large = (tf_a, tf_b) if len(tf_a) <= len(tf_b) else (tf_b, tf_a)
    for term, freq in small.items():
        w_a = freq * idf.get(term, 0.0)
        w_b = large.get(term, 0) * idf.get(term, 0.0)
        if w_a == 0 and w_b == 0:
            continue
        dot += w_a * w_b
        na += w_a * w_a
    # large 剩余维度的平方和
    for term, freq in large.items():
        if term in small:
            continue
        w = freq * idf.get(term, 0.0)
        nb += w * w
    # 再补 small 全部维度（已经包含在 small 的循环里）
    for term, freq in small.items():
        w = freq * idf.get(term, 0.0)
        # 注意：na 已经在上面算过一次，不能重复加
    _ = na  # silence unused
    # 正确重算：把 na 清零重算
    na2 = 0.0
    for term, freq in tf_a.items():
        w = freq * idf.get(term, 0.0)
        na2 += w * w
    nb2 = 0.0
    for term, freq in tf_b.items():
        w = freq * idf.get(term, 0.0)
        nb2 += w * w
    if na2 <= 1e-12 or nb2 <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, dot / (math.sqrt(na2) * math.sqrt(nb2))))


def jaccard(a: set[int], b: set[int]) -> float:
    """Jaccard 相似度（标签交集）。"""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def exponential_decay(
    published_at: datetime | None, half_life_days: float = TIME_HALF_LIFE_DAYS
) -> float:
    """以 half_life 为半衰期的指数衰减；无日期给 0.4（中等偏旧）。"""
    if not published_at:
        return 0.4
    now = datetime.now(UTC)
    pub = published_at
    if pub.tzinfo is None:
        from datetime import timezone

        pub = pub.replace(tzinfo=timezone.utc)
    days = max(0.0, (now - pub).total_seconds() / 86400.0)
    return math.exp(-DECAY_LAMBDA * days) + 0.05 * math.exp(-days / half_life_days)


def heat_score(views: int, likes: int, comments: int) -> float:
    """对数归一化的互动热度（0~1 近似）。"""
    v_term = math.log1p(max(0, views)) / math.log(10_000)
    likes_term = math.log1p(max(0, likes)) / math.log(500)
    c_term = math.log1p(max(0, comments)) / math.log(200)
    # 加权后夹到 0-1
    raw = 0.45 * v_term + 0.30 * likes_term + 0.25 * c_term
    return max(0.0, min(1.0, raw))


# ══════════════════════════════════════════════════════════════════
#  RecommendationService
# ══════════════════════════════════════════════════════════════════


class RecommendationService:
    """多信号推荐 + 相似文章 + 热榜 + 搜索打分复用。"""

    def __init__(self, db: AsyncSession, cache: CacheService | None = None) -> None:
        self._db = db
        self._cache = cache or CacheService()

    # ─────────────── 1. 相似文章 ───────────────
    async def get_similar_posts(self, post_id: int, limit: int = 6) -> list[Post]:
        """基于 TF-IDF + 标签 + 分类 + 时间的综合相关度。"""
        cache_key = f"simv2:{post_id}:{limit}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        # ── 取当前文章 ──
        base_q = (
            select(Post)
            .options(selectinload(Post.tags), selectinload(Post.category))
            .where(Post.id == post_id, Post.status == "published")
        )
        res = await self._db.execute(base_q)
        anchor = res.scalar_one_or_none()
        if anchor is None:
            return []

        anchor_tag_ids: set[int] = {t.id for t in anchor.tags}
        anchor_cat = anchor.category_id
        anchor_text = normalize_text(
            self._first_lang(anchor.title)
            + " "
            + self._first_lang(anchor.excerpt)
            + " "
            + self._first_lang(anchor.content)
        )
        anchor_tokens = tokenize(anchor_text)
        anchor_tf = build_tf(anchor_tokens)

        # ── 候选池：同分类 + 同标签最多 300 篇 ──
        cand_q = (
            select(Post.id)
            .outerjoin(post_tags, Post.id == post_tags.c.post_id)
            .where(
                Post.id != post_id,
                Post.status == "published",
                or_(
                    (post_tags.c.tag_id.in_(list(anchor_tag_ids))) if anchor_tag_ids else False,
                    (Post.category_id == anchor_cat) if anchor_cat else False,
                ),
            )
            .group_by(Post.id)
            .limit(300)
        )
        cand_res = await self._db.execute(cand_q)
        candidate_ids = [row[0] for row in cand_res.fetchall()]

        # 候选不足时按时间补热门
        if len(candidate_ids) < limit * 6:
            supplement_q = (
                select(Post.id)
                .where(Post.id != post_id, Post.status == "published")
                .order_by(func.coalesce(Post.published_at, Post.created_at).desc())
                .limit(max(0, limit * 6 - len(candidate_ids)))
            )
            sup = await self._db.execute(supplement_q)
            for row in sup.fetchall():
                if row[0] not in candidate_ids:
                    candidate_ids.append(row[0])

        if not candidate_ids:
            await self._cache.set(cache_key, [], ttl=SIMILAR_POSTS_TTL)
            return []

        # ── 一次性拉取所有候选全文 / tags ──
        full_q = (
            select(Post)
            .options(
                selectinload(Post.tags), selectinload(Post.category), selectinload(Post.author)
            )
            .where(Post.id.in_(candidate_ids))
        )
        full_res = await self._db.execute(full_q)
        candidates = full_res.scalars().all()
        candidates_by_id = {p.id: p for p in candidates}

        # ── 聚合 IDF（只基于候选集的 document frequency）──
        doc_tokens_map: dict[int, list[str]] = {}
        df: Counter[str] = Counter()
        n_docs = 1 + len(candidates)  # anchor + 候选
        for p in candidates:
            text = normalize_text(
                self._first_lang(p.title)
                + " "
                + self._first_lang(p.excerpt)
                + " "
                + self._first_lang(p.content)
            )
            toks = tokenize(text)
            doc_tokens_map[p.id] = toks
            for term in set(toks):
                df[term] += 1
        # anchor 也计入 IDF
        for term in set(anchor_tokens):
            df[term] += 1
        idf: dict[str, float] = {
            term: math.log(1 + (n_docs / (1 + freq))) for term, freq in df.items()
        }

        # ── 聚合 likes / comments / views 热数据 ──
        heat_q = (
            select(
                Post.id,
                Post.views,
                func.count(func.distinct(post_likes.c.user_id)).label("lc"),
                func.count(func.distinct(Comment.id)).label("cc"),
            )
            .outerjoin(post_likes, Post.id == post_likes.c.post_id)
            .outerjoin(Comment, (Post.id == Comment.post_id) & (Comment.active.is_(True)))
            .where(Post.id.in_(list(candidates_by_id.keys())))
            .group_by(Post.id)
        )
        heat_rows = await self._db.execute(heat_q)
        heat_map: dict[int, tuple[int, int, int]] = {}
        for r in heat_rows.fetchall():
            heat_map[r.id] = (int(r.views or 0), int(r.lc or 0), int(r.cc or 0))

        # ── 逐篇打分 ──
        scored: list[tuple[int, float]] = []
        anchor_cat_id = anchor_cat
        for cid, cand in candidates_by_id.items():
            cand_tag_ids: set[int] = {t.id for t in cand.tags}
            tag_sim = jaccard(anchor_tag_ids, cand_tag_ids)
            cat_sim = 1.0 if (anchor_cat_id and cand.category_id == anchor_cat_id) else 0.0

            cand_tokens = doc_tokens_map.get(cid, [])
            cand_tf = build_tf(cand_tokens)
            text_sim = compute_cosine_similarity(anchor_tf, cand_tf, idf)

            # BM25 风格的文档长度归一化：对文本相似度做修正
            dl = max(1, len(cand_tokens))
            len_norm = (1 - BM25_B) + BM25_B * (dl / AVG_DOC_LEN_ESTIMATE)
            text_sim_bm25 = text_sim / max(0.3, len_norm)

            ts = exponential_decay(cand.published_at or cand.created_at)
            views, lc, cc = heat_map.get(cid, (0, 0, 0))
            hs = heat_score(views, lc, cc)

            w = SIMILAR_WEIGHTS
            total = (
                w["tags"] * tag_sim
                + w["category"] * cat_sim
                + w["tfidf"] * max(text_sim, text_sim_bm25)
                + w["time"] * ts
                + w["heat"] * hs
            )
            scored.append((cid, total))

        # ── 排序 & 补足 ──
        scored.sort(key=lambda x: x[1], reverse=True)
        selected_ids = [cid for cid, _ in scored[:limit]]
        if len(selected_ids) < limit:
            existing = set(selected_ids) | {post_id}
            fill_q = (
                select(Post)
                .options(
                    selectinload(Post.author), selectinload(Post.category), selectinload(Post.tags)
                )
                .where(Post.id.notin_(list(existing)), Post.status == "published")
                .order_by(Post.views.desc())
                .limit(limit - len(selected_ids))
            )
            fill_res = await self._db.execute(fill_q)
            posts_top = fill_res.scalars().all()
            result = [candidates_by_id[i] for i in selected_ids if i in candidates_by_id]
            result.extend(posts_top)
        else:
            result = [candidates_by_id[i] for i in selected_ids if i in candidates_by_id]

        await self._cache.set(cache_key, result, ttl=SIMILAR_POSTS_TTL)
        return result

    # ─────────────── 2. 首页推荐（多臂老虎机 ε-greedy）───────────────
    async def get_recommended_posts(
        self,
        user_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        exclude_post_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        cache_key = self._cache.build_key_with_hash(
            "recsv2",
            user=user_id or "anon",
            p=page,
            ps=page_size,
            excl=",".join(str(i) for i in sorted(exclude_post_ids or [])),
        )
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        exclude_ids = set(exclude_post_ids or [])
        import random

        explore_mode = user_id is None and random.random() < EXPLORE_EPSILON

        user_tag_prefs: Counter[int] = Counter()
        if user_id:
            user_tag_prefs = await self._get_user_tag_preferences(user_id)

        # ── 批量取所有 published 候选 ──
        stats_q = (
            select(
                Post.id,
                Post.views,
                Post.published_at,
                Post.created_at,
                Post.category_id,
                func.count(func.distinct(post_likes.c.user_id)).label("lc"),
                func.count(func.distinct(Comment.id)).label("cc"),
            )
            .outerjoin(post_likes, Post.id == post_likes.c.post_id)
            .outerjoin(Comment, (Post.id == Comment.post_id) & (Comment.active.is_(True)))
            .where(Post.status == "published")
            .group_by(Post.id)
        )
        stats_rows = await self._db.execute(stats_q)
        post_stats: dict[int, dict[str, Any]] = {}
        for r in stats_rows.fetchall():
            post_stats[r.id] = {
                "views": int(r.views or 0),
                "lc": int(r.lc or 0),
                "cc": int(r.cc or 0),
                "published_at": r.published_at or r.created_at,
                "category_id": r.category_id,
            }
        all_ids = list(post_stats.keys())
        if not all_ids:
            empty: dict[str, Any] = {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 1,
            }
            await self._cache.set(cache_key, empty, ttl=RECOMMENDATION_TTL)
            return empty

        # ── 批量取 tag ──
        tags_q = select(post_tags.c.post_id, post_tags.c.tag_id).where(
            post_tags.c.post_id.in_(all_ids)
        )
        tags_res = await self._db.execute(tags_q)
        post_to_tags: dict[int, list[int]] = {}
        for pid, tid in tags_res.fetchall():
            post_to_tags.setdefault(pid, []).append(tid)

        prefs_total = sum(user_tag_prefs.values()) or 1

        scored: list[tuple[int, float]] = []
        for pid, stats in post_stats.items():
            if pid in exclude_ids:
                continue
            hs = heat_score(stats["views"], stats["lc"], stats["cc"])
            ts = exponential_decay(stats["published_at"])

            # 用户标签偏好匹配（UCB 风格 bonus）
            tag_bonus = 0.0
            if user_tag_prefs:
                matched = sum(user_tag_prefs.get(tid, 0) for tid in post_to_tags.get(pid, []))
                tag_bonus = min(1.0, matched / prefs_total)

            # UCB 风格上置信界：时间越久未知，探索权重越低（反之新文章鼓励曝光）
            ucb = hs + 0.25 * ts + 0.20 * tag_bonus

            # ε-greedy：探索模式下引入随机抖动（-0.05 ~ +0.30）鼓励冷门/最新
            if explore_mode:
                ucb += random.uniform(-0.05, 0.30)
            scored.append((pid, ucb))

        scored.sort(key=lambda x: x[1], reverse=True)

        total = len(scored)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = [pid for pid, _ in scored[start:end]]

        items: list[Post] = []
        if page_ids:
            detail_q = (
                select(Post)
                .options(
                    selectinload(Post.author), selectinload(Post.category), selectinload(Post.tags)
                )
                .where(Post.id.in_(page_ids))
            )
            detail_res = await self._db.execute(detail_q)
            m = {p.id: p for p in detail_res.scalars().all()}
            items = [m[i] for i in page_ids if i in m]

        out = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total else 1,
        }
        await self._cache.set(cache_key, out, ttl=RECOMMENDATION_TTL)
        return out

    # ─────────────── 3. 热榜（Hacker News 风格热度）───────────────
    async def get_hot_posts(self, limit: int = 10, days: int = 30) -> list[Post]:
        cache_key = f"hotv2:{limit}:{days}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        cutoff = datetime.now(UTC) - timedelta(days=days)
        q = (
            select(
                Post.id,
                Post.views,
                func.coalesce(func.count(func.distinct(post_likes.c.user_id)), 0).label("lc"),
                func.coalesce(func.count(func.distinct(Comment.id)), 0).label("cc"),
                Post.published_at,
                Post.created_at,
            )
            .outerjoin(post_likes, Post.id == post_likes.c.post_id)
            .outerjoin(Comment, (Post.id == Comment.post_id) & (Comment.active.is_(True)))
            .where(
                Post.status == "published",
                func.coalesce(Post.published_at, Post.created_at) >= cutoff,
            )
            .group_by(Post.id)
        )
        rows = await self._db.execute(q)

        scored: list[tuple[int, float]] = []
        for r in rows.fetchall():
            views = int(r.views or 0)
            lc = int(r.lc or 0)
            cc = int(r.cc or 0)
            pub = r.published_at or r.created_at
            # 裸 SQL 结果列（GROUP BY select）从 SQLite/Postgres 读回可能为 offset-naive，
            # 与 datetime.now(UTC) 相减会 TypeError: can't subtract offset-naive and offset-aware。
            # 同文件 exponential_decay() L177-L179 的一致处理：缺 tzinfo 补 UTC。
            if pub is not None and pub.tzinfo is None:
                from datetime import timezone

                pub = pub.replace(tzinfo=timezone.utc)
            age_hours = max(1.0, (datetime.now(UTC) - pub).total_seconds() / 3600.0)
            # HN 经典公式：(v + 10·l + 20·c) / (age+2)^1.8
            score = (views + 10 * lc + 20 * cc) / ((age_hours + 2.0) ** 1.8)
            scored.append((r.id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        top_ids = [i for i, _ in scored[:limit]]

        items: list[Post] = []
        if top_ids:
            dq = (
                select(Post)
                .options(
                    selectinload(Post.author), selectinload(Post.category), selectinload(Post.tags)
                )
                .where(Post.id.in_(top_ids))
            )
            dr = await self._db.execute(dq)
            m = {p.id: p for p in dr.scalars().all()}
            items = [m[i] for i in top_ids if i in m]
        await self._cache.set(cache_key, items, ttl=HOT_RANKING_TTL)
        return items

    # ─────────────── 4. 搜索评分（BM25-Okapi 风格字段加权）───────────────
    async def search_rerank(
        self,
        query: str,
        posts: list[Post],
        language: str = "zh",
    ) -> list[tuple[Post, float]]:
        """对已召回的 Post 候选做 BM25 风格精细化排序。

        权重：title × 3.0 + tags × 2.0 + excerpt × 1.5 + content × 1.0
        """
        q = normalize_text(query)
        q_tokens = tokenize(q)
        if not q_tokens or not posts:
            return [(p, 0.0) for p in posts]

        q_terms = set(q_tokens)
        n_docs = len(posts)

        # 1-pass：统计每个 term 的 document frequency（跨候选集）
        df: Counter[str] = Counter()
        docs_data: list[dict[str, Any]] = []
        for p in posts:
            title_toks = tokenize(normalize_text(self._get_localized(p.title, language)))
            excerpt_toks = tokenize(normalize_text(self._get_localized(p.excerpt, language)))
            content_toks = tokenize(normalize_text(self._get_localized(p.content, language)))
            tag_toks: list[str] = []
            for t in getattr(p, "tags", []) or []:
                tag_toks.extend(tokenize(normalize_text(self._get_localized(t.name, language))))
            for term in set(title_toks) | set(excerpt_toks) | set(content_toks) | set(tag_toks):
                if term in q_terms:
                    df[term] += 1
            docs_data.append(
                {
                    "p": p,
                    "title": Counter(title_toks),
                    "excerpt": Counter(excerpt_toks),
                    "content": Counter(content_toks),
                    "tags": Counter(tag_toks),
                    "dl": len(title_toks) + len(excerpt_toks) + len(content_toks) + len(tag_toks),
                }
            )

        avg_dl = max(1.0, sum(d["dl"] for d in docs_data) / max(1, len(docs_data)))
        idf_q = {
            term: math.log(1 + ((n_docs - freq + 0.5) / (freq + 0.5))) for term, freq in df.items()
        }

        # 2-pass：对每个 doc，按字段权重累加 BM25 分数
        ranked: list[tuple[Post, float]] = []
        for d in docs_data:
            score = 0.0
            dl_norm = (1 - BM25_B) + BM25_B * (d["dl"] / avg_dl)
            for term in q_terms:
                if term not in idf_q:
                    continue
                term_idf = idf_q[term]
                field_acc = 0.0
                for fld, fw in BM25_FIELD_WEIGHTS:
                    tf = int(d[fld].get(term, 0))
                    if tf <= 0:
                        continue
                    num = tf * (BM25_K1 + 1)
                    den = tf + BM25_K1 * dl_norm
                    field_acc += fw * (num / den)
                score += term_idf * field_acc
            ranked.append((d["p"], score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    # ─────────────── 内部 helper ───────────────

    @staticmethod
    def _first_lang(value: Any) -> str:
        """从 i18n dict 或 plain string 抽取首个可用文本。"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("zh", "en", "ja", "zh_Hant"):
                if value.get(key):
                    return str(value[key])
            for v in value.values():
                if v:
                    return str(v)
        return str(value) if value else ""

    @staticmethod
    def _get_localized(value: Any, language: str) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            if language in value and value[language]:
                return str(value[language])
            # 回退链
            for key in ("zh", "en", "ja", "zh_Hant"):
                if value.get(key):
                    return str(value[key])
            for v in value.values():
                if v:
                    return str(v)
        return str(value) if value else ""

    async def _get_user_tag_preferences(self, user_id: int | None, days: int = 30) -> Counter[int]:
        if not user_id:
            return Counter()
        cutoff = datetime.now(UTC) - timedelta(days=days)
        q = (
            select(post_tags.c.tag_id, func.count(post_tags.c.tag_id).label("n"))
            .select_from(PostViewHistory)
            .join(Post, PostViewHistory.post_id == Post.id)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                PostViewHistory.user_id == user_id,
                PostViewHistory.viewed_at >= cutoff,
            )
            .group_by(post_tags.c.tag_id)
        )
        rows = await self._db.execute(q)
        pref: Counter[int] = Counter()
        for r in rows.fetchall():
            pref[int(r.tag_id)] = int(r.n or 0)
        return pref


async def get_recommendation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache_service)],
) -> RecommendationService:
    """FastAPI 依赖注入工厂。"""
    return RecommendationService(db, cache)
