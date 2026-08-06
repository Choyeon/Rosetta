#!/usr/bin/env python
"""
Rosetta API 基准测试脚本

测试 API 的响应时间和吞吐量。
"""

import asyncio
import statistics
import time
import sys

import httpx


async def benchmark_sequential(client: httpx.AsyncClient, endpoint: str, requests: int = 100):
    """顺序请求测试"""
    latencies = []
    errors = 0

    for _ in range(requests):
        start = time.perf_counter()
        try:
            resp = await client.get(endpoint)
            if resp.status_code != 200:
                errors += 1
        except Exception:
            errors += 1
        latencies.append((time.perf_counter() - start) * 1000)

    return latencies, errors


async def benchmark_concurrent(client: httpx.AsyncClient, endpoint: str, concurrency: int, total: int):
    """并发请求测试"""
    semaphore = asyncio.Semaphore(concurrency)

    async def make_request():
        async with semaphore:
            start = time.perf_counter()
            try:
                resp = await client.get(endpoint)
                return (time.perf_counter() - start) * 1000, resp.status_code
            except Exception:
                return (time.perf_counter() - start) * 1000, 0

    start_time = time.perf_counter()
    results = await asyncio.gather(*[make_request() for _ in range(total)])
    total_time = time.perf_counter() - start_time

    latencies = sorted([r[0] for r in results])
    success = sum(1 for r in results if r[1] == 200)

    return latencies, total_time, success


async def main():
    base_url = "http://127.0.0.1:8000"

    print("=" * 70)
    print("🚀 Rosetta API 基准测试")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0, proxy=None) as client:
        endpoints = [
            ("/health", "健康检查"),
            ("/api/config", "站点配置"),
            ("/api/blog/categories", "分类列表"),
            ("/api/blog/tags", "标签列表"),
        ]

        print("\n📊 顺序请求测试 (100次请求)")
        print("-" * 70)

        seq_results = []
        for endpoint, name in endpoints:
            latencies, errors = await benchmark_sequential(client, endpoint, 100)
            if latencies:
                avg = statistics.mean(latencies)
                latencies_sorted = sorted(latencies)
                p50 = latencies_sorted[50]
                p95 = latencies_sorted[95]
                rps = 1000 / avg if avg > 0 else 0
                success_rate = (100 - errors) / 100 * 100

                print(f"{name:<12} | 平均: {avg:>6.2f}ms | P50: {p50:>5.1f}ms | "
                      f"P95: {p95:>5.1f}ms | RPS: {rps:>5.0f} | 成功率: {success_rate:.0f}%")
                seq_results.append((name, avg, p95))

        print("\n📊 并发压力测试")
        print("-" * 70)

        test_configs = [
            ("/health", 10, 500),
            ("/health", 50, 1000),
            ("/health", 100, 2000),
            ("/api/config", 10, 500),
            ("/api/config", 50, 1000),
        ]

        for endpoint, concurrency, total in test_configs:
            latencies, total_time, success = await benchmark_concurrent(
                client, endpoint, concurrency, total
            )
            if latencies:
                avg = statistics.mean(latencies)
                p95 = latencies[int(len(latencies) * 0.95)]
                rps = total / total_time
                success_rate = success / total * 100

                print(f"{endpoint:<20} | {concurrency:>3}并发 | RPS: {rps:>7.1f} | "
                      f"平均: {avg:>6.2f}ms | P95: {p95:>6.1f}ms | 成功: {success_rate:.0f}%")

        print("\n" + "=" * 70)
        print("📈 性能总结")
        print("=" * 70)

        if seq_results:
            avg_latency = statistics.mean([r[1] for r in seq_results])
            avg_p95 = statistics.mean([r[2] for r in seq_results])
            print(f"平均延迟: {avg_latency:.2f}ms")
            print(f"平均P95: {avg_p95:.1f}ms")

            if avg_latency < 10:
                print("性能评级: ⭐⭐⭐⭐⭐ 优秀 (<10ms)")
            elif avg_latency < 50:
                print("性能评级: ⭐⭐⭐⭐ 良好 (10-50ms)")
            elif avg_latency < 100:
                print("性能评级: ⭐⭐⭐ 一般 (50-100ms)")
            else:
                print("性能评级: ⭐⭐ 需要优化 (>100ms)")

        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
