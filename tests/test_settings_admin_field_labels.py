"""后台「站点设置」每一把设置键都必须有条目文案，且不能有多余的文案。

`settings.vue` 的字段标签是 `label = { ... }[key] ?? key` 的兜底形态：**漏一条键不会报错，
只会把原始 snake_case 键名当标签显示**（表现是设置页出现 `police_icp_number`、
`show_powered_by` 这种条目，管理员只能靠猜）。同一条兜底还让"已删键的遗留文案"永远隐身——
所以这里两侧都钉：

1. 后端分组默认值里的每一把键，必须在通用标签表、该组的 `GROUP_LABELS` 覆写、
   专用编辑器白名单（`GROUP_EDITOR_KEYS`）或 Customizer 去重屏蔽名单
   （`GROUP_BLOCK_KEYS`）里出现，否则它会以裸键名渲染。
2. 通用标签表里不得有"后端任何分组都不再声明"的键——那是下一份死清单。
3. 屏蔽/编辑器名单里的键必须真的存在于该组默认值：拼错的键名等于"以为藏起来了，
   实际还在页面上形成第二个写入口"（appearance 的 primary_color 就是被 Customizer
   重复的那一类，漏屏蔽即双真相源）。
4. 左侧分组标签页的集合必须等于后端 `_GROUP_DEFAULTS` 的键集：少一个 tab 就是
   "整组设置没有任何界面能读到或写入"。
5. 出现在多个分组里的同名键（`enable` / `title` / `description`…）只允许一组靠通用文案兜底，
   其余组必须有 `GROUP_LABELS` 覆写——通用表按键名查，同名必然有一组标签驴唇不对马嘴。

区间镜像（输入框 min/max ⇔ `_NUMERIC_BOUNDS`）与"每个键都有真实消费点"分别由
`frontend/tests/unit/inertSettingSwitches.spec.ts` 与 `tests/test_settings_group_consumers.py`
钉，本文件不重复。
"""

import re
from pathlib import Path

from backend.api.settings_groups import _GROUP_DEFAULTS, _default_for

SETTINGS_PAGE = Path("frontend/pages/admin/system/settings.vue")


def _page() -> str:
    raw = SETTINGS_PAGE.read_text(encoding="utf-8")
    # Windows 工作树是 CRLF，解析里的 `\n}` / `\n]` 锚点必须先归一，否则守卫会假报"结构已变"。
    return raw.replace("\r\n", "\n")


def _generic_label_keys() -> set[str]:
    src = _page()
    start = src.index("const label = {")
    end = src.index("}[key] ?? key", start)
    return set(re.findall(r"([A-Za-z_0-9]+):\s*'", src[start:end]))


def _group_label_overrides() -> dict[str, set[str]]:
    src = _page()
    start = src.index("const GROUP_LABELS")
    end = src.index("\n}", start)
    out: dict[str, set[str]] = {}
    for group, body in re.findall(r"(\w+):\s*\{([^}]*)\}", src[start:end]):
        out[group] = set(re.findall(r"([A-Za-z_0-9]+):", body))
    return out


def _set_keys(declaration: str) -> set[str]:
    match = re.search(rf"const {declaration} = new Set<string>\(([^)]*)\)", _page())
    if not match:
        raise AssertionError(f"settings.vue 里找不到 `{declaration}`，本守卫的解析口径已失效")
    return set(re.findall(r"'([A-Za-z_0-9]+)'", match.group(1)))


def _editor_keys_by_group() -> dict[str, set[str]]:
    src = _page()
    match = re.search(r"const GROUP_EDITOR_KEYS[^=]*= \{([\s\S]*?)\n\}", src)
    if not match:
        raise AssertionError("settings.vue 里找不到 GROUP_EDITOR_KEYS，解析口径已失效")
    out: dict[str, set[str]] = {}
    for group, body in re.findall(r"(\w+):\s*new Set<string>\((\[.*?\])\)", match.group(1)):
        out[group] = set(re.findall(r"'([A-Za-z_0-9]+)'", body))
    return out


def _blocked_keys_by_group() -> dict[str, set[str]]:
    src = _page()
    match = re.search(r"const GROUP_BLOCK_KEYS[^=]*= \{([\s\S]*?)\n\}", src)
    if not match:
        raise AssertionError("settings.vue 里找不到 GROUP_BLOCK_KEYS，解析口径已失效")
    out: dict[str, set[str]] = {}
    for group, setter in re.findall(r"(\w+):\s*(\w+_BLOCK_KEYS)", match.group(1)):
        out[group] = _set_keys(setter)
    return out


def _tab_groups() -> set[str]:
    src = _page()
    match = re.search(r"\nconst groups = \[([\s\S]*?)\n\]", src)
    if not match:
        raise AssertionError("settings.vue 里找不到分组清单 `const groups`，解析口径已失效")
    return set(re.findall(r"\{ key: '(\w+)'", match.group(1)))


def test_the_guard_itself_still_parses():
    """解析失效时上面每条断言都会变成"空集相等"的恒真假绿，所以先清点数量。"""
    assert len(_generic_label_keys()) >= 60, "通用标签表解析出的条目异常少，正则口径要复查"
    overrides = _group_label_overrides()
    assert set(overrides) == {"basic", "hero", "notice", "donate", "footer"}, (
        f"GROUP_LABELS 覆写的分组集合变了：{sorted(overrides)}"
    )
    assert _editor_keys_by_group()["donate"] == {"methods", "sponsors"}
    blocked = _blocked_keys_by_group()
    assert blocked["appearance"] == {"primary_color", "accent_color", "page_width_px"}
    assert blocked["footer"] == {"copyright", "icp_number"}
    assert len(_tab_groups()) == len(_GROUP_DEFAULTS) >= 14


def test_setting_groups_have_exactly_one_admin_tab_each():
    assert _tab_groups() == set(_GROUP_DEFAULTS), (
        "后台分组 tab 与后端分组默认值不一致：tab 少一组等于那组设置没有任何界面能读写，"
        "tab 多一组则点开就是空白"
    )


def test_every_setting_key_has_an_admin_label():
    generic = _generic_label_keys()
    overrides = _group_label_overrides()
    editors = _editor_keys_by_group()
    blocked = _blocked_keys_by_group()

    bare = []
    for group in sorted(_GROUP_DEFAULTS):
        visible = generic | overrides.get(group, set())
        hidden = editors.get(group, set()) | blocked.get(group, set())
        for key in _default_for(group):
            if key not in visible and key not in hidden:
                bare.append(f"{group}.{key}")

    assert bare == [], f"这些设置键在后台会以裸键名渲染：{bare}"


def test_no_label_entry_is_a_dead_key():
    declared: set[str] = set()
    for group in _GROUP_DEFAULTS:
        declared |= set(_default_for(group))
    dead = sorted(_generic_label_keys() - declared)
    assert dead == [], f"标签表里这些键后端已不再声明（死文案，会误导下一个改这里的人）：{dead}"

    for group, keys in _group_label_overrides().items():
        assert group in _GROUP_DEFAULTS, f"GROUP_LABELS 覆写了一个不存在的分组：{group}"
        orphan = sorted(keys - set(_default_for(group)))
        assert orphan == [], f"{group} 组的标签覆写指向已不存在的键：{orphan}"


def test_hidden_key_lists_reference_real_keys():
    for group, keys in _editor_keys_by_group().items():
        assert group in _GROUP_DEFAULTS, f"GROUP_EDITOR_KEYS 里有不存在的分组：{group}"
        missing = sorted(keys - set(_default_for(group)))
        assert missing == [], f"{group} 组专用编辑器名单里的键后端不声明：{missing}"

    for group, keys in _blocked_keys_by_group().items():
        assert group in _GROUP_DEFAULTS, f"GROUP_BLOCK_KEYS 里有不存在的分组：{group}"
        missing = sorted(keys - set(_default_for(group)))
        assert missing == [], (
            f"{group} 组屏蔽名单里的键后端不声明（拼错的名字等于没屏蔽，"
            f"页面上会留下与主题自定义重复的第二个写入口）：{missing}"
        )


def test_shared_key_names_are_overridden_in_every_but_one_group():
    """同名键出现在多个分组时，通用标签只可能写对其中一组。

    通用表是 `{ enable: '启用评论功能' }[key] ?? key` 这种**按键名**查的表：`enable` 同时是
    comments / hero / notice / donate 四组的键，其余三组不覆写就会显示"启用评论功能"，
    管理员在捐助页看到这句只会以为页面上多了一块评论。所以除"文案原本所属的那一组"以外，
    每个用到同名键的分组都必须有 `GROUP_LABELS` 覆写。
    """
    generic = _generic_label_keys()
    overrides = _group_label_overrides()

    users: dict[str, list[str]] = {}
    for group in _GROUP_DEFAULTS:
        for key in _default_for(group):
            users.setdefault(key, []).append(group)

    ambiguous = []
    for key, groups in sorted(users.items()):
        if len(groups) < 2 or key not in generic:
            continue
        relying_on_generic = [g for g in groups if key not in overrides.get(g, set())]
        if len(relying_on_generic) > 1:
            ambiguous.append(f"{key} -> {relying_on_generic}")
    assert ambiguous == [], (
        "同名键在多个分组里都靠通用文案兜底，至少有一组的标签是错的：" + "; ".join(ambiguous)
    )


def test_donate_json_keys_are_editor_owned_not_generic():
    """donate.methods / donate.sponsors 是对象数组，落进通用 schema 会退化成裸 JSON 文本域。"""
    editors = _editor_keys_by_group().get("donate", set())
    assert {"methods", "sponsors"} <= editors
    src = _page()
    for ref in ("donateMethods", "donateSponsors"):
        assert src.count(ref) >= 3, f"专用编辑器 `{ref}` 看起来没接上（引用次数异常）"


def test_notice_group_documents_the_two_announcement_surfaces():
    """顶部横幅与侧栏公告列表是两套东西，description 与开关文案都必须说清边界。"""
    src = _page()
    assert "公告管理" in src, "公告分组说明必须指出多条公告走「公告管理」"
    notice_desc = re.search(r"\{ key: 'notice',.*?desc: '([^']*)'", src, re.S)
    assert notice_desc and "顶部横幅" in notice_desc.group(1)
    overrides = _group_label_overrides().get("notice", set())
    assert "enable" in overrides, "notice.enable 必须有覆写文案"
    enable_help = re.search(r"notice: \{[\s\S]*?enable: '([^']*)'", src)
    assert enable_help and "公告管理" in enable_help.group(1), (
        "notice.enable 的文案必须说清它只管顶部横幅，不管公告管理里的那一批"
    )
