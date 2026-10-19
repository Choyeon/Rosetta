"""站点设置分组的 PATCH 语义：局部保存不得清空同组其它配置。

历史缺陷：_save_group 以「默认值」而非「库里已存的值」为底做合并，
只发一个键的 PATCH 会把同组其余项静默打回默认。Admin 界面每次提交整组，
所以这条在 UI 上从未暴露；插件/脚本走 API 做局部保存即成配置丢失。
"""

from httpx import AsyncClient


async def _patch(client: AsyncClient, headers: dict, group: str, payload: dict) -> dict:
    resp = await client.patch(f"/api/settings/{group}", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_partial_patch_keeps_other_keys_of_the_same_group(
    client: AsyncClient, admin_headers: dict
):
    await _patch(
        client,
        admin_headers,
        "footer",
        {"slogan": "保留我", "text": "页脚文字", "show_back_to_top": False},
    )

    saved = await _patch(client, admin_headers, "footer", {"copyright": "© 2099 只改这一项"})

    assert saved["data"]["slogan"] == "保留我"
    assert saved["data"]["text"] == "页脚文字"
    assert saved["data"]["show_back_to_top"] is False
    assert saved["data"]["copyright"] == "© 2099 只改这一项"

    fetched = await client.get("/api/settings/footer", headers=admin_headers)
    assert fetched.status_code == 200
    data = fetched.json()["data"]
    assert data["slogan"] == "保留我"
    assert data["show_back_to_top"] is False


async def test_partial_patch_still_ignores_unknown_keys(client: AsyncClient, admin_headers: dict):
    await _patch(client, admin_headers, "footer", {"slogan": "白名单外不生效"})

    saved = await _patch(client, admin_headers, "footer", {"not_a_setting_key": "x"})

    assert "not_a_setting_key" not in saved["data"]
    assert saved["data"]["slogan"] == "白名单外不生效"
