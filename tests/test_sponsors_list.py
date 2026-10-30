"""打赏名单（donate.sponsors）契约回归：一条写口、一份真源、一个开关管两侧。

起因：``GET /api/sponsors`` 历史上读的是 ``site_configs`` 里 ``key='SPONSORS'`` 这条
**没有任何写入方**的 KV（设置页不写、环境变量不写），而前台 /sponsor 只渲染收款码，
于是这个公开端点长期是一份"看起来有数据源、实际永远为空"的死读口；
``/api/config`` 的 ``sponsor_show_sponsors_list`` 同样没有消费点。

现在名单的唯一真源是 donate 分组（后台「捐助打赏」编辑器写入），本文件钉住四件事：

① 分组默认键集里有 ``sponsors`` 与 ``show_sponsors_list``（否则 ``_save_group`` 的
   ``if k in base`` 会把设置页提交的名单静默丢弃——写了存不进）；
② PATCH donate 后 ``GET /api/sponsors`` 立刻拿到新名单（端点自有一族 30 分钟响应缓存，
   不在分组保存时删掉它，就是"后台改了名单、接口最长 30 分钟仍吐旧的"）；
③ ``show_sponsors_list`` 是唯一开关，且**两侧都生效**：前台隐藏、公开接口同样回空。
   只挡渲染的开关等于名单照样对外公开；
④ 存量站点只写过旧 KV 时仍然读得到（回退路径不因收口而丢数据）。
"""

import json

from backend.api.settings_groups import _default_for
from backend.models.core import SiteConfig


async def _patch_donate(client, staff_headers, payload: dict) -> dict:
    resp = await client.patch("/api/settings/donate", json=payload, headers=staff_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_donate_group_has_sponsor_keys():
    base = _default_for("donate")
    assert "sponsors" in base and base["sponsors"] == []
    assert base["show_sponsors_list"] is True


async def test_sponsors_read_saved_group_list(client, staff_headers):
    saved = await _patch_donate(
        client,
        staff_headers,
        {
            "sponsors": [
                {"name": "张三", "avatar": "/media/a.png", "amount": "¥50", "date": "2026-10-01"},
                {"name": "", "amount": "¥10"},  # 空昵称行由设置页剥离，读口再挡一次
                {"name": "李四"},
            ]
        },
    )
    assert len(saved["sponsors"]) == 3  # 分组保存的是原样数组（清洗发生在编辑器与读口）

    rows = await client.get("/api/sponsors")
    assert rows.status_code == 200, rows.text
    names = [item["name"] for item in rows.json()]
    assert names == ["张三", "李四"]
    first = rows.json()[0]
    assert first["avatar"] == "/media/a.png"
    assert first["amount"] == "¥50"
    assert first["date"] == "2026-10-01"
    # 缺字段的行补空串，不能下发 None（前台 :alt / {{ }} 都要拿到字符串）
    assert rows.json()[1] == {"name": "李四", "avatar": "", "amount": "", "date": ""}


async def test_sponsors_cache_purged_on_donate_save(client, staff_headers):
    """先读一次把结果写进端点缓存，再改名单——第二次读必须是新值。"""
    first = await client.get("/api/sponsors")
    assert first.json() == []

    await _patch_donate(client, staff_headers, {"sponsors": [{"name": "王五", "amount": "¥20"}]})

    second = await client.get("/api/sponsors")
    assert [item["name"] for item in second.json()] == ["王五"]


async def test_disable_flag_closes_every_donation_surface(client, staff_headers):
    """``enable=false`` 是"本站不再接受捐助"：公开设置与打赏名单必须同时收起。

    关闭前 ``enable`` 只影响前端 noindex 与页脚入口：``GET /api/settings/public`` 照样下发
    收款方式、``GET /api/sponsors`` 照样吐名单——直接访问 /sponsor 仍看得见收款码。
    三个公开面必须同一条判据，重新打开也要能完整恢复。
    """
    methods = [{"name": "支付宝", "image": "/media/qr.png", "note": ""}]
    await _patch_donate(
        client,
        staff_headers,
        {"enable": True, "methods": methods, "sponsors": [{"name": "钱八"}]},
    )

    public = (await client.get("/api/settings/public")).json()["groups"]["donate"]
    assert public["methods"] == methods
    assert [item["name"] for item in public["sponsors"]] == ["钱八"]
    assert [item["name"] for item in (await client.get("/api/sponsors")).json()] == ["钱八"]

    await _patch_donate(client, staff_headers, {"enable": False})

    public = (await client.get("/api/settings/public")).json()["groups"]["donate"]
    assert public["enable"] is False
    assert public["methods"] == [], "关掉捐助后公开设置不该继续下发收款码"
    assert public["sponsors"] == []
    assert public["show_sponsors_list"] is False
    assert (await client.get("/api/sponsors")).json() == []

    # 重新打开必须完整恢复：把"关闭"做成单向清空等于丢掉运营者配置
    await _patch_donate(client, staff_headers, {"enable": True})
    public = (await client.get("/api/settings/public")).json()["groups"]["donate"]
    assert public["methods"] == methods
    assert [item["name"] for item in public["sponsors"]] == ["钱八"]
    assert [item["name"] for item in (await client.get("/api/sponsors")).json()] == ["钱八"]


async def test_sponsors_flag_gates_the_public_read_surface(client, staff_headers):
    await _patch_donate(
        client,
        staff_headers,
        {"sponsors": [{"name": "赵六"}, {"name": "孙七"}]},
    )
    assert len((await client.get("/api/sponsors")).json()) == 2

    await _patch_donate(client, staff_headers, {"show_sponsors_list": False})
    assert (await client.get("/api/sponsors")).json() == []

    await _patch_donate(client, staff_headers, {"show_sponsors_list": True})
    assert len((await client.get("/api/sponsors")).json()) == 2


async def test_sponsors_are_projected_to_public_settings(client, staff_headers):
    """前台读的是 /settings/public 里的 donate 分组：新键必须出现在那份投影里，
    否则 /sponsor 的打赏墙永远拿不到名单（端点对了、页面还是空的）。"""
    await _patch_donate(
        client, staff_headers, {"sponsors": [{"name": "周八", "date": "2026-10-02"}]}
    )
    pub = await client.get("/api/settings/public")
    assert pub.status_code == 200, pub.text
    donate = pub.json()["groups"]["donate"]
    assert donate["show_sponsors_list"] is True
    assert [item["name"] for item in donate["sponsors"]] == ["周八"]


async def test_sponsors_fall_back_to_legacy_site_config(client, db_session):
    """存量站点只写过 key='SPONSORS'：分组没名单时仍要读得到旧数据。"""
    db_session.add(
        SiteConfig(
            key="SPONSORS",
            value=json.dumps(
                [{"name": "旧名单读者", "amount": "¥5"}, {"no_name": True}],
                ensure_ascii=False,
            ),
            description="legacy",
        )
    )
    await db_session.commit()

    rows = await client.get("/api/sponsors")
    assert [item["name"] for item in rows.json()] == ["旧名单读者"]


async def test_sponsors_broken_legacy_json_is_empty(client, db_session):
    db_session.add(SiteConfig(key="SPONSORS", value="{not json", description="legacy"))
    await db_session.commit()
    assert (await client.get("/api/sponsors")).json() == []
