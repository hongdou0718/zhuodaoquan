#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import math
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from email.utils import format_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
DIST = ROOT / "dist"
CONTENT = ROOT / "content"
POSTS_DIR = CONTENT / "posts"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"


@dataclass(frozen=True)
class Post:
    title: str
    date: date
    summary: str
    tag: str
    body: str
    slug: str
    draft: bool

    @property
    def date_iso(self) -> str:
        return self.date.isoformat()

    @property
    def date_display(self) -> str:
        return self.date.strftime("%Y.%m.%d")

    @property
    def reading_minutes(self) -> int:
        plain = re.sub(r"[#>*_`\[\]()!-]", "", self.body)
        chinese_count = len(re.findall(r"[\u3400-\u9fff]", plain))
        word_count = len(re.findall(r"\b[A-Za-z]+\b", plain))
        return max(1, math.ceil((chinese_count + word_count) / 450))


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Front matter must be enclosed by --- lines")

    metadata: dict[str, str] = {}
    for raw_line in parts[1].splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        cleaned = value.strip()
        if (
            len(cleaned) >= 2
            and cleaned[0] == cleaned[-1]
            and cleaned[0] in {"'", '"'}
        ):
            cleaned = cleaned[1:-1]
        metadata[key.strip()] = cleaned
    return metadata, parts[2].lstrip()


def load_posts(include_drafts: bool = False) -> list[Post]:
    posts: list[Post] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        metadata, body = parse_front_matter(path.read_text(encoding="utf-8"))
        filename_date = re.match(r"(\d{4}-\d{2}-\d{2})-", path.stem)
        date_text = metadata.get("date") or (
            filename_date.group(1) if filename_date else date.today().isoformat()
        )
        slug = metadata.get("slug") or re.sub(
            r"^\d{4}-\d{2}-\d{2}-", "", path.stem
        )
        draft = metadata.get("draft", "false").lower() == "true"
        if draft and not include_drafts:
            continue
        posts.append(
            Post(
                title=metadata.get("title", path.stem),
                date=date.fromisoformat(date_text),
                summary=metadata.get("summary", ""),
                tag=metadata.get("tag", "随笔"),
                body=body,
                slug=slug,
                draft=draft,
            )
        )
    return sorted(posts, key=lambda post: post.date, reverse=True)


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def render_inline(source: str) -> str:
    placeholders: list[str] = []

    def hold(fragment: str) -> str:
        token = f"\x00INLINE{len(placeholders)}\x00"
        placeholders.append(fragment)
        return token

    source = re.sub(
        r"`([^`\n]+)`",
        lambda match: hold(f"<code>{escape(match.group(1))}</code>"),
        source,
    )
    source = re.sub(
        r"!\[([^\]]*)\]\(([^)\s]+)\)",
        lambda match: hold(
            f'<img src="{escape(match.group(2))}" '
            f'alt="{escape(match.group(1))}" loading="lazy" decoding="async">'
        ),
        source,
    )
    source = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda match: hold(
            f'<a href="{escape(match.group(2))}">'
            f"{escape(match.group(1))}</a>"
        ),
        source,
    )

    rendered = html.escape(source, quote=False)
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"__(.+?)__", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", rendered)
    rendered = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<em>\1</em>", rendered)

    for index, fragment in enumerate(placeholders):
        rendered = rendered.replace(f"\x00INLINE{index}\x00", fragment)
    return rendered


def markdown_to_html(source: str) -> str:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        fence = re.match(r"^```([\w-]*)\s*$", stripped)
        if fence:
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            language = fence.group(1)
            class_name = (
                f' class="language-{escape(language)}"' if language else ""
            )
            output.append(
                f"<pre><code{class_name}>"
                f"{html.escape(chr(10).join(code_lines), quote=False)}"
                "</code></pre>"
            )
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            output.append(
                f"<h{level}>{render_inline(heading.group(2).strip())}</h{level}>"
            )
            index += 1
            continue

        if re.match(r"^(---+|\*\*\*+|___+)$", stripped):
            output.append("<hr>")
            index += 1
            continue

        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(
                    re.sub(r"^\s*>\s?", "", lines[index], count=1)
                )
                index += 1
            output.append(
                f"<blockquote>{markdown_to_html(chr(10).join(quote_lines))}"
                "</blockquote>"
            )
            continue

        unordered = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if unordered:
            items = []
            while index < len(lines):
                item = re.match(r"^\s*[-*+]\s+(.+)$", lines[index])
                if not item:
                    break
                items.append(f"<li>{render_inline(item.group(1))}</li>")
                index += 1
            output.append("<ul>\n" + "\n".join(items) + "\n</ul>")
            continue

        ordered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if ordered:
            items = []
            while index < len(lines):
                item = re.match(r"^\s*\d+\.\s+(.+)$", lines[index])
                if not item:
                    break
                items.append(f"<li>{render_inline(item.group(1))}</li>")
                index += 1
            output.append("<ol>\n" + "\n".join(items) + "\n</ol>")
            continue

        paragraph: list[str] = []
        while index < len(lines):
            current = lines[index]
            current_stripped = current.strip()
            if not current_stripped:
                break
            if (
                current_stripped.startswith(">")
                or re.match(r"^#{1,6}\s+", current_stripped)
                or re.match(r"^```", current_stripped)
                or re.match(r"^\s*[-*+]\s+", current)
                or re.match(r"^\s*\d+\.\s+", current)
                or re.match(r"^(---+|\*\*\*+|___+)$", current_stripped)
            ):
                break
            paragraph.append(current)
            index += 1
        output.append(
            "\n".join(
                f"<p>{render_inline(current.strip())}</p>"
                for current in paragraph
                if current.strip()
            )
        )

    return "\n".join(output)


def absolute_url(path: str) -> str:
    base = SITE.get("base_url", "").rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}" if base else clean_path


def render_fragment(template_name: str, replacements: dict[str, str]) -> str:
    template = (TEMPLATES / template_name).read_text(encoding="utf-8")
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def nav_markup(root: str, active: str) -> str:
    items = [
        ("home", "首页", f"{root}index.html"),
        ("archive", "文章", f"{root}index.html#archive"),
        ("about", "关于", f"{root}about.html"),
    ]
    links = []
    for key, label, href in items:
        current = ' aria-current="page"' if key == active else ""
        active_class = " is-active" if key == active else ""
        links.append(
            f'<a class="nav-link{active_class}" href="{href}"{current}>{label}</a>'
        )
    return "\n        ".join(links)


def base_page(
    *,
    root: str,
    page_title: str,
    description: str,
    content: str,
    active: str,
    body_class: str,
    og_type: str = "website",
    og_title: str | None = None,
    meta_extra: str = "",
) -> str:
    return render_fragment(
        "base.html",
        {
            "root": root,
            "page_title": escape(page_title),
            "description": escape(description),
            "og_type": og_type,
            "og_title": escape(og_title or page_title),
            "meta_extra": meta_extra,
            "site_title": escape(SITE["title"]),
            "author": escape(SITE["author"]),
            "nav": nav_markup(root, active),
            "content": content,
            "body_class": body_class,
            "year": str(date.today().year),
        },
    )


def post_list_item(post: Post, index: int) -> str:
    search_value = " ".join(
        [post.title, post.summary, post.tag, post.date_display]
    ).lower()
    return f"""
    <li class="post-item" data-search="{escape(search_value)}" data-tag="{escape(post.tag)}">
      <a class="post-link" href="posts/{escape(post.slug)}.html">
        <span class="post-number">{index:02d}</span>
        <span class="post-main">
          <time datetime="{post.date_iso}">{post.date_display}</time>
          <h3 class="post-title">{escape(post.title)}</h3>
          <span class="post-summary">{escape(post.summary)}</span>
        </span>
        <span class="post-side">
          <span class="tag">{escape(post.tag)}</span>
          <span class="reading-time">约 {post.reading_minutes} 分钟</span>
          <svg class="icon post-arrow" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 17 17 7M7 7h10v10"></path>
          </svg>
        </span>
      </a>
    </li>"""


def navigation_card(post: Post | None, direction: str) -> str:
    if post is None:
        return f'<span class="post-navigation__item is-empty">{direction}</span>'
    label = "上一篇" if direction == "上一篇" else "下一篇"
    return f"""
    <a class="post-navigation__item" href="{escape(post.slug)}.html">
      <span>{label}</span>
      <strong>{escape(post.title)}</strong>
    </a>"""


def build_posts(posts: list[Post]) -> None:
    posts_output = DIST / "posts"
    posts_output.mkdir(parents=True, exist_ok=True)
    for index, post in enumerate(posts):
        previous_post = posts[index - 1] if index > 0 else None
        next_post = posts[index + 1] if index + 1 < len(posts) else None
        article_content = render_fragment(
            "article.html",
            {
                "date_iso": post.date_iso,
                "date_display": post.date_display,
                "tag": escape(post.tag),
                "reading_minutes": str(post.reading_minutes),
                "title": escape(post.title),
                "summary": escape(post.summary),
                "article_body": markdown_to_html(post.body),
                "post_navigation": (
                    navigation_card(previous_post, "上一篇")
                    + navigation_card(next_post, "下一篇")
                ),
            },
        )
        canonical = (
            f'<link rel="canonical" href="{escape(absolute_url(f"posts/{post.slug}.html"))}">'
            if SITE.get("base_url")
            else ""
        )
        page = base_page(
            root="../",
            page_title=f"{post.title} · {SITE['title']}",
            description=post.summary or SITE["description"],
            content=article_content,
            active="archive",
            body_class="article-page",
            og_type="article",
            meta_extra=canonical,
        )
        (posts_output / f"{post.slug}.html").write_text(page, encoding="utf-8")


def build_home(posts: list[Post]) -> None:
    tag_counts = Counter(post.tag for post in posts)
    tag_filters = "\n      ".join(
        f'<button class="tag-filter" type="button" data-tag="{escape(tag)}">'
        f"{escape(tag)} <span>{count}</span></button>"
        for tag, count in sorted(tag_counts.items())
    )
    post_list = "\n".join(
        post_list_item(post, index) for index, post in enumerate(posts, start=1)
    )
    content = render_fragment(
        "index.html",
        {
            "site_title": escape(SITE["title"]),
            "tagline": escape(SITE["tagline"]),
            "home_note": escape(SITE["home_note"]),
            "about_summary": escape(SITE["about_summary"]),
            "post_count": str(len(posts)),
            "tag_filters": tag_filters,
            "post_list": post_list,
        },
    )
    canonical = (
        f'<link rel="canonical" href="{escape(absolute_url("index.html"))}">'
        if SITE.get("base_url")
        else ""
    )
    page = base_page(
        root="",
        page_title=f"{SITE['title']} · {SITE['tagline']}",
        description=SITE["description"],
        content=content,
        active="home",
        body_class="home-page",
        meta_extra=canonical,
    )
    (DIST / "index.html").write_text(page, encoding="utf-8")


def build_about() -> None:
    metadata, body = parse_front_matter(
        (CONTENT / "about.md").read_text(encoding="utf-8")
    )
    del metadata
    content = render_fragment(
        "about.html",
        {
            "tagline": escape(SITE["tagline"]),
            "about_body": markdown_to_html(body),
        },
    )
    canonical = (
        f'<link rel="canonical" href="{escape(absolute_url("about.html"))}">'
        if SITE.get("base_url")
        else ""
    )
    page = base_page(
        root="",
        page_title=f"关于 · {SITE['title']}",
        description=SITE["about_summary"],
        content=content,
        active="about",
        body_class="about-page",
        meta_extra=canonical,
    )
    (DIST / "about.html").write_text(page, encoding="utf-8")


def build_not_found() -> None:
    content = render_fragment("404.html", {"root": ""})
    page = base_page(
        root="",
        page_title=f"页面未找到 · {SITE['title']}",
        description="页面未找到",
        content=content,
        active="",
        body_class="not-found-page",
    )
    (DIST / "404.html").write_text(page, encoding="utf-8")


def build_feed(posts: list[Post]) -> None:
    items = []
    for post in posts:
        published = datetime.combine(post.date, time(9, 0), tzinfo=timezone.utc)
        items.append(
            f"""
    <item>
      <title>{escape(post.title)}</title>
      <link>{escape(absolute_url(f"posts/{post.slug}.html"))}</link>
      <guid>{escape(absolute_url(f"posts/{post.slug}.html"))}</guid>
      <pubDate>{format_datetime(published)}</pubDate>
      <description>{escape(post.summary)}</description>
    </item>"""
        )
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(SITE["title"])}</title>
    <link>{escape(absolute_url(""))}</link>
    <description>{escape(SITE["description"])}</description>
    <language>zh-CN</language>
    <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>
    {"".join(items)}
  </channel>
</rss>
"""
    (DIST / "feed.xml").write_text(feed, encoding="utf-8")


def build_sitemap(posts: list[Post]) -> None:
    urls = ["index.html", "about.html"] + [
        f"posts/{post.slug}.html" for post in posts
    ]
    entries = "\n".join(
        f"  <url><loc>{escape(absolute_url(path))}</loc></url>" for path in urls
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    (DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (DIST / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n"
        f"Sitemap: {absolute_url('sitemap.xml')}\n",
        encoding="utf-8",
    )


def copy_assets() -> None:
    assets_output = DIST / "assets"
    assets_output.mkdir(parents=True, exist_ok=True)
    for filename in (
        "style.css",
        "site.js",
        "writing-desk.webp",
        "paper-grain.webp",
        "favicon.svg",
    ):
        source = ASSETS / filename
        if source.exists():
            shutil.copy2(source, assets_output / filename)
    (DIST / "_headers").write_text(
        "/assets/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n\n"
        "/*.html\n"
        "  Cache-Control: public, max-age=0, must-revalidate\n",
        encoding="utf-8",
    )
    (DIST / ".nojekyll").write_text("", encoding="utf-8")


def build() -> None:
    global DIST

    output = ROOT / "dist"
    staging = ROOT / ".dist-build"
    backup = ROOT / ".dist-backup"

    if staging.exists():
        shutil.rmtree(staging)
    if backup.exists():
        shutil.rmtree(backup)

    DIST = staging
    DIST.mkdir(parents=True)

    try:
        posts = load_posts()
        copy_assets()
        build_home(posts)
        build_about()
        build_posts(posts)
        build_not_found()
        build_feed(posts)
        build_sitemap(posts)

        if output.exists():
            output.rename(backup)
        DIST.rename(output)
        if backup.exists():
            shutil.rmtree(backup)
        DIST = output
    except Exception:
        if DIST.exists():
            shutil.rmtree(DIST)
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise

    print(f"Built {len(posts)} posts into {DIST}")


if __name__ == "__main__":
    build()
