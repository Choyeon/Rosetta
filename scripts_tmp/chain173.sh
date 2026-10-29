#!/usr/bin/env bash
# chain173：robots/llms 也补齐软过期窗口（swr 处理器在 staleMaxAge 缺省时会发裸 stale-while-revalidate）
cd /root/www/Rosetta || exit 1
echo "===== 01 pull ====="
git pull --ff-only origin main || { echo "[173] FAIL pull"; echo "RESULT: FAIL"; exit 1; }
git log --oneline -1
cd frontend || exit 1

echo "===== 02 frontend gates (serial) ====="
pnpm lint > /tmp/g173_lint.log 2>&1; rc=$?
echo "[173] lint rc=$rc |$(grep -E '✖ [0-9]+ problems?' /tmp/g173_lint.log | tail -1)|"
pnpm typecheck > /tmp/g173_tc.log 2>&1; echo "[173] typecheck rc=$? ts_errors=$(grep -c 'error TS' /tmp/g173_tc.log)"
pnpm test > /tmp/g173_test.log 2>&1; rc=$?
echo "[173] vitest rc=$rc |$(sed -e 's/\x1b\[[0-9;]*m//g' /tmp/g173_test.log | grep -E 'Tests +[0-9]+ (passed|failed)' | tail -1)|"
pnpm build > /tmp/g173_build.log 2>&1; rc=$?
echo "[173] build rc=$rc tail=$(tail -2 /tmp/g173_build.log | tr '\n' ' ')"
echo "[173] build-slop=$(grep -cE 'Hydration node mismatch|Failed to fetch|/api/api|CORS error' /tmp/g173_build.log)"

echo "===== 03 restart frontend only ====="
systemctl restart panel-rosetta-frontend.service
for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ || true)
  [ "$code" = "200" ] && break
  sleep 2
done
echo "[173] nitro=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/) https_home=$(curl -s -o /dev/null -w '%{http_code}' https://choyeon.cc/)"

fail=0
echo "===== 04 /authors 四条语言变体进 sitemap-pages ====="
body=$(curl -s https://choyeon.cc/sitemap-pages.xml)
for u in "https://choyeon.cc/authors" "https://choyeon.cc/en/authors" "https://choyeon.cc/ja/authors" "https://choyeon.cc/zh_Hant/authors"; do
  n=$(printf '%s' "$body" | grep -o "<loc>$u</loc>" | wc -l | tr -d ' ')
  echo "[173] loc $u => $n"
  [ "$n" = "1" ] || { echo "[173] FAIL loc $u count=$n"; fail=1; }
done

echo "===== 05 feed 头口径（RFC 5861：软过期窗口必须带秒值）====="
check_feed() {
  local p="$1" want_cc="$2" want_ct="$3"
  local hdr cc ct
  hdr=$(curl -s -o /dev/null -D - "https://choyeon.cc$p")
  cc=$(printf '%s' "$hdr" | grep -i '^cache-control:' | tr -d '\r' | sed -e 's/^[Cc]ache-[Cc]ontrol: *//')
  ct=$(printf '%s' "$hdr" | grep -i '^content-type:' | tr -d '\r' | sed -e 's/^[Cc]ontent-[Tt]ype: *//')
  echo "[173] $p ct=$ct cc=$cc"
  [ "$ct" = "$want_ct" ] || { echo "[173] FAIL content-type $p ($ct)"; fail=1; }
  [ "$cc" = "$want_cc" ] || { echo "[173] FAIL cache-control $p ($cc)"; fail=1; }
  case "$cc" in *"stale-while-revalidate,"*|*"stale-while-revalidate" ) echo "[173] FAIL bare swr on $p"; fail=1 ;; esac
}
check_feed "/sitemap-pages.xml" "s-maxage=3600, stale-while-revalidate=86400" "application/xml; charset=utf-8"
check_feed "/sitemap-posts.xml" "s-maxage=3600, stale-while-revalidate=86400" "application/xml; charset=utf-8"
check_feed "/sitemap-taxonomies.xml" "s-maxage=3600, stale-while-revalidate=86400" "application/xml; charset=utf-8"
check_feed "/sitemap.xml" "s-maxage=3600, stale-while-revalidate=86400" "application/xml; charset=utf-8"
check_feed "/rss.xml" "s-maxage=1800, stale-while-revalidate=86400" "application/rss+xml; charset=utf-8"
check_feed "/robots.txt" "s-maxage=3600, stale-while-revalidate=86400" "text/plain; charset=utf-8"
check_feed "/llms.txt" "s-maxage=3600, stale-while-revalidate=86400" "text/plain; charset=utf-8"
check_feed "/.well-known/security.txt" "s-maxage=3600, stale-while-revalidate=86400" "text/plain; charset=utf-8"

echo "===== 06 正常页不受影响 ====="
for p in "/" "/posts" "/authors" "/posts/hot"; do
  cc=$(curl -s -o /dev/null -D - "https://choyeon.cc$p" | grep -i '^cache-control:' | tr -d '\r' | sed -e 's/^[Cc]ache-[Cc]ontrol: *//')
  echo "[173] $p cache-control=$cc"
  case "$cc" in *no-store*) echo "[173] FAIL normal page became no-store: $p"; fail=1 ;; esac
  case "$cc" in *s-maxage*) ;; *) echo "[173] FAIL normal page lost s-maxage: $p"; fail=1 ;; esac
done

echo "===== 07 后台/登录页仍是 no-store ====="
for p in "/login" "/admin"; do
  cc=$(curl -s -o /dev/null -D - "https://choyeon.cc$p" | grep -i '^cache-control:' | tr -d '\r' | sed -e 's/^[Cc]ache-[Cc]ontrol: *//')
  echo "[173] $p cache-control=$cc"
  case "$cc" in *no-store*) ;; *) echo "[173] FAIL backend page lost no-store: $p"; fail=1 ;; esac
done

[ "$fail" = 0 ] && echo "RESULT: PASS" || echo "RESULT: FAIL"
echo "CHAIN done"
