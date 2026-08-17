"""
Mock 数据生成脚本

使用 Faker 生成真实的测试数据。
运行方式: python -m backend.scripts.mock_data
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

from faker import Faker
from sqlalchemy import select

from backend.core.auth import get_password_hash
from backend.core.database import async_session_maker
from backend.models.activity import Activity
from backend.models.announcement import Announcement
from backend.models.blog import Category, Comment, Post, Tag
from backend.models.core import FriendLink, Navigation
from backend.models.user import User

fake = Faker("zh_CN")
fake_en = Faker("en_US")


def create_multilang(zh: str, en: str = "", ja: str = "", zh_hant: str = "") -> dict:
    """创建多语言字段"""
    return {
        "zh": zh,
        "en": en or zh,
        "ja": ja or zh,
        "zh_Hant": zh_hant or zh,
    }


CATEGORIES_DATA = [
    {
        "name": create_multilang("技术", "Technology", "技術", "技術"),
        "slug": "technology",
        "description": create_multilang(
            "技术相关文章", "Technology related articles", "技術関連の記事", "技術相關文章"
        ),
        "color": "#3B82F6",
        "icon": "heroicons:code-bracket",
    },
    {
        "name": create_multilang("生活", "Lifestyle", "生活", "生活"),
        "slug": "lifestyle",
        "description": create_multilang(
            "生活随笔", "Lifestyle articles", "生活エッセイ", "生活隨筆"
        ),
        "color": "#10B981",
        "icon": "heroicons:heart",
    },
    {
        "name": create_multilang("教程", "Tutorial", "チュートリアル", "教程"),
        "slug": "tutorial",
        "description": create_multilang(
            "各类教程", "Various tutorials", "各種チュートリアル", "各類教程"
        ),
        "color": "#F59E0B",
        "icon": "heroicons:academic-cap",
    },
    {
        "name": create_multilang("随笔", "Essay", "エッセイ", "隨筆"),
        "slug": "essay",
        "description": create_multilang(
            "随笔杂谈", "Essays and thoughts", "エッセイと随想", "隨筆雜談"
        ),
        "color": "#8B5CF6",
        "icon": "heroicons:pencil-square",
    },
]

TAGS_DATA = [
    {
        "name": create_multilang("Python", "Python", "Python", "Python"),
        "slug": "python",
        "color": "#3776AB",
    },
    {
        "name": create_multilang("JavaScript", "JavaScript", "JavaScript", "JavaScript"),
        "slug": "javascript",
        "color": "#F7DF1E",
    },
    {"name": create_multilang("Vue", "Vue", "Vue", "Vue"), "slug": "vue", "color": "#4FC08D"},
    {
        "name": create_multilang("React", "React", "React", "React"),
        "slug": "react",
        "color": "#61DAFB",
    },
    {
        "name": create_multilang("FastAPI", "FastAPI", "FastAPI", "FastAPI"),
        "slug": "fastapi",
        "color": "#009688",
    },
    {
        "name": create_multilang("Docker", "Docker", "Docker", "Docker"),
        "slug": "docker",
        "color": "#2496ED",
    },
    {
        "name": create_multilang("数据库", "Database", "データベース", "數據庫"),
        "slug": "database",
        "color": "#00758F",
    },
    {
        "name": create_multilang("前端", "Frontend", "フロントエンド", "前端"),
        "slug": "frontend",
        "color": "#61DAFB",
    },
    {
        "name": create_multilang("后端", "Backend", "バックエンド", "後端"),
        "slug": "backend",
        "color": "#68A063",
    },
    {
        "name": create_multilang("算法", "Algorithm", "アルゴリズム", "算法"),
        "slug": "algorithm",
        "color": "#E34C26",
    },
    {
        "name": create_multilang("工具", "Tools", "ツール", "工具"),
        "slug": "tools",
        "color": "#FF6B6B",
    },
    {"name": create_multilang("Git", "Git", "Git", "Git"), "slug": "git", "color": "#F05032"},
]

ARTICLE_TEMPLATES = [
    {
        "title_zh": "深入理解 Python 异步编程",
        "title_en": "Deep Dive into Python Async Programming",
        "category": "tutorial",
        "tags": ["python", "backend"],
        "code_language": "python",
        "code_snippet": '''import asyncio
from typing import AsyncGenerator

async def fetch_data(url: str) -> dict:
    """异步获取数据"""
    await asyncio.sleep(1)  # 模拟网络请求
    return {"url": url, "data": "response"}

async def process_batch(urls: list[str]) -> list[dict]:
    """并发处理多个请求"""
    tasks = [fetch_data(url) for url in urls]
    return await asyncio.gather(*tasks)

async def stream_data(count: int) -> AsyncGenerator[int, None]:
    """异步生成器示例"""
    for i in range(count):
        await asyncio.sleep(0.1)
        yield i

async def main():
    urls = ["https://api.example.com/1", "https://api.example.com/2"]
    results = await process_batch(urls)
    print(f"Processed {len(results)} requests")

    async for num in stream_data(5):
        print(f"Streamed: {num}")

if __name__ == "__main__":
    asyncio.run(main())''',
        "content_zh": """# 深入理解 Python 异步编程

Python 的异步编程是现代 Python 开发中不可或缺的技能。本文将深入探讨 asyncio 的工作原理和最佳实践。

## 什么是异步编程？

异步编程允许程序在等待 I/O 操作时执行其他任务，从而提高整体效率。与传统的同步编程不同，异步编程使用事件循环来管理任务调度。

## 核心概念

### 1. 协程 (Coroutine)

协程是异步编程的基本单元，使用 `async def` 定义：

```python
async def my_coroutine():
    await some_async_operation()
```

### 2. 事件循环 (Event Loop)

事件循环是异步程序的核心，负责调度和执行协程：

```python
loop = asyncio.get_event_loop()
loop.run_until_complete(my_coroutine())
```

### 3. 任务 (Task)

任务是对协程的封装，可以并发执行：

```python
task = asyncio.create_task(my_coroutine())
```

## 实际应用示例

下面是一个完整的异步数据处理示例：

```python
{code}
```

## 最佳实践

1. **避免阻塞操作**：在异步代码中不要使用阻塞的 I/O 操作
2. **合理使用并发**：使用 `asyncio.gather()` 并发执行多个任务
3. **错误处理**：使用 try-except 捕获异步操作中的异常
4. **资源管理**：使用 async with 管理异步上下文

## 性能对比

| 方式 | 100 个请求耗时 |
|------|---------------|
| 同步 | ~100 秒 |
| 异步 | ~1 秒 |

异步编程在 I/O 密集型场景下性能提升显著。

## 总结

Python 异步编程虽然有一定学习曲线，但掌握后将大大提升程序的性能和可扩展性。建议在实际项目中逐步尝试和应用。
""",
        "content_en": """# Deep Dive into Python Async Programming

Python's async programming is an essential skill for modern Python development. This article explores how asyncio works and best practices.

## What is Async Programming?

Async programming allows programs to perform other tasks while waiting for I/O operations, improving overall efficiency.

## Core Concepts

### 1. Coroutine

Coroutines are the basic unit of async programming:

```python
async def my_coroutine():
    await some_async_operation()
```

### 2. Event Loop

The event loop is the core of async programs:

```python
loop = asyncio.get_event_loop()
loop.run_until_complete(my_coroutine())
```

### 3. Task

Tasks wrap coroutines for concurrent execution:

```python
task = asyncio.create_task(my_coroutine())
```

## Practical Example

```python
{code}
```

## Best Practices

1. **Avoid blocking operations**
2. **Use concurrency wisely**
3. **Handle errors properly**
4. **Manage resources with async with**

## Performance Comparison

| Method | 100 requests time |
|--------|-------------------|
| Sync | ~100 seconds |
| Async | ~1 second |

## Summary

Python async programming has a learning curve but significantly improves performance in I/O-bound scenarios.
""",
    },
    {
        "title_zh": "Vue 3 组合式 API 完全指南",
        "title_en": "Complete Guide to Vue 3 Composition API",
        "category": "tutorial",
        "tags": ["vue", "javascript", "frontend"],
        "code_language": "vue",
        "code_snippet": """<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

interface Props {
  initialCount?: number
}

const props = withDefaults(defineProps<Props>(), {
  initialCount: 0
})

const emit = defineEmits<{
  change: [value: number]
}>()

// 响应式状态
const count = ref(props.initialCount)
const step = ref(1)

// 计算属性
const doubled = computed(() => count.value * 2)
const isEven = computed(() => count.value % 2 === 0)

// 方法
function increment() {
  count.value += step.value
  emit('change', count.value)
}

function decrement() {
  count.value -= step.value
  emit('change', count.value)
}

// 监听器
watch(count, (newVal, oldVal) => {
  console.log(`Count changed: ${oldVal} -> ${newVal}`)
})

// 生命周期
onMounted(() => {
  console.log('Counter mounted')
})

onUnmounted(() => {
  console.log('Counter unmounted')
})
</script>

<template>
  <div class="counter">
    <p>Count: {{ count }}</p>
    <p>Doubled: {{ doubled }}</p>
    <p>Is Even: {{ isEven }}</p>

    <div class="controls">
      <button @click="decrement">-</button>
      <button @click="increment">+</button>
    </div>

    <input v-model.number="step" type="number" min="1" />
  </div>
</template>

<style scoped>
.counter {
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.controls {
  display: flex;
  gap: 0.5rem;
  margin: 1rem 0;
}

button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background: #42b883;
  color: white;
  cursor: pointer;
}

button:hover {
  background: #3aa876;
}
</style>""",
        "content_zh": """# Vue 3 组合式 API 完全指南

Vue 3 引入的组合式 API (Composition API) 彻底改变了我们编写 Vue 组件的方式。本文将全面介绍其用法。

## 为什么需要组合式 API？

在大型应用中，Options API 可能导致：

- 相关逻辑分散在不同选项中
- 代码复用困难
- TypeScript 支持不够完善

组合式 API 解决了这些问题。

## 基础用法

### setup 函数

```javascript
export default {
  setup() {
    const count = ref(0)
    return { count }
  }
}
```

### `<script setup>` 语法糖

这是更简洁的写法：

```vue
<script setup>
import { ref } from 'vue'
const count = ref(0)
</script>
```

## 完整组件示例

下面是一个功能完整的计数器组件：

```{code_language}
{code}
```

## 响应式 API 详解

### ref

用于基本类型的响应式包装：

```javascript
const count = ref(0)
count.value++ // 需要使用 .value
```

### reactive

用于对象的响应式包装：

```javascript
const state = reactive({
  name: 'Vue',
  version: 3
})
state.name = 'Vue 3' // 直接访问
```

### computed

创建计算属性：

```javascript
const doubled = computed(() => count.value * 2)
```

### watch

监听数据变化：

```javascript
watch(count, (newVal, oldVal) => {
  console.log(`Changed: ${oldVal} -> ${newVal}`)
})
```

## 组合式函数

提取和复用逻辑：

```javascript
// useCounter.js
export function useCounter(initial = 0) {
  const count = ref(initial)
  const increment = () => count.value++
  const decrement = () => count.value--

  return { count, increment, decrement }
}
```

## 生命周期钩子

| Options API | Composition API |
|-------------|-----------------|
| created | setup() |
| mounted | onMounted |
| updated | onUpdated |
| unmounted | onUnmounted |

## 最佳实践

1. 使用 `<script setup>` 简化代码
2. 将相关逻辑组织在一起
3. 提取可复用逻辑为组合式函数
4. 合理使用 TypeScript 类型

## 总结

组合式 API 提供了更灵活的代码组织方式，特别适合大型项目和 TypeScript 用户。
""",
        "content_en": """# Complete Guide to Vue 3 Composition API

Vue 3's Composition API has completely changed how we write Vue components. This guide covers everything you need to know.

## Why Composition API?

In large applications, Options API can lead to:

- Related logic scattered across options
- Difficult code reuse
- Poor TypeScript support

Composition API solves these problems.

## Basic Usage

### setup Function

```javascript
export default {
  setup() {
    const count = ref(0)
    return { count }
  }
}
```

### `<script setup>` Syntax

A more concise approach:

```vue
<script setup>
import { ref } from 'vue'
const count = ref(0)
</script>
```

## Complete Component Example

```{code_language}
{code}
```

## Reactive API Details

### ref

For primitive types:

```javascript
const count = ref(0)
count.value++ // Use .value
```

### reactive

For objects:

```javascript
const state = reactive({
  name: 'Vue',
  version: 3
})
```

### computed

Create computed properties:

```javascript
const doubled = computed(() => count.value * 2)
```

### watch

Watch for changes:

```javascript
watch(count, (newVal, oldVal) => {
  console.log(`Changed: ${oldVal} -> ${newVal}`)
})
```

## Composables

Extract and reuse logic:

```javascript
// useCounter.js
export function useCounter(initial = 0) {
  const count = ref(initial)
  const increment = () => count.value++

  return { count, increment }
}
```

## Lifecycle Hooks

| Options API | Composition API |
|-------------|-----------------|
| created | setup() |
| mounted | onMounted |
| updated | onUpdated |
| unmounted | onUnmounted |

## Summary

Composition API provides more flexible code organization, especially for large projects and TypeScript users.
""",
    },
    {
        "title_zh": "Docker 容器化最佳实践",
        "title_en": "Docker Containerization Best Practices",
        "category": "technology",
        "tags": ["docker", "tools"],
        "code_language": "dockerfile",
        "code_snippet": """# 多阶段构建示例
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建
RUN npm run build

# 生产镜像
FROM node:20-alpine AS runner

WORKDIR /app

# 安全：使用非 root 用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制构建产物
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV NODE_ENV=production

CMD ["node", "server.js"]""",
        "content_zh": """# Docker 容器化最佳实践

Docker 已经成为现代应用部署的标准工具。本文介绍 Docker 容器化的最佳实践。

## 为什么选择 Docker？

- **一致性**：开发、测试、生产环境完全一致
- **隔离性**：应用之间相互隔离
- **可移植性**：一次构建，到处运行
- **版本控制**：镜像可以版本化管理

## Dockerfile 最佳实践

### 1. 使用多阶段构建

多阶段构建可以显著减小镜像体积：

```{code_language}
{code}
```

### 2. 优化层缓存

```dockerfile
# 好的做法：先复制依赖文件
COPY package*.json ./
RUN npm install

# 再复制源代码
COPY . .
```

### 3. 使用 .dockerignore

```
node_modules
npm-debug.log
Dockerfile
.dockerignore
.git
.gitignore
```

### 4. 安全实践

```dockerfile
# 使用特定版本，而不是 latest
FROM node:20-alpine

# 使用非 root 用户
RUN adduser -D appuser
USER appuser

# 设置只读文件系统
# docker run --read-only ...
```

## Docker Compose 示例

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: secret

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

## 常用命令

```bash
# 构建镜像
docker build -t myapp:latest .

# 运行容器
docker run -d -p 3000:3000 myapp:latest

# 查看日志
docker logs -f <container_id>

# 进入容器
docker exec -it <container_id> sh

# 清理无用镜像
docker image prune -a
```

## 镜像优化技巧

| 技巧 | 效果 |
|------|------|
| 使用 Alpine 基础镜像 | 减小 80% 体积 |
| 多阶段构建 | 减小 50% 体积 |
| 合并 RUN 指令 | 减少层数 |
| 使用 .dockerignore | 避免复制无用文件 |

## 总结

遵循这些最佳实践，可以构建出安全、高效、可维护的 Docker 镜像。
""",
        "content_en": """# Docker Containerization Best Practices

Docker has become the standard tool for modern application deployment. This article covers best practices for Docker containerization.

## Why Docker?

- **Consistency**: Identical environments across dev, test, and production
- **Isolation**: Applications are isolated from each other
- **Portability**: Build once, run anywhere
- **Version Control**: Images can be versioned

## Dockerfile Best Practices

### 1. Use Multi-stage Builds

Multi-stage builds significantly reduce image size:

```{code_language}
{code}
```

### 2. Optimize Layer Cache

```dockerfile
# Good: Copy dependency files first
COPY package*.json ./
RUN npm install

# Then copy source code
COPY . .
```

### 3. Use .dockerignore

```
node_modules
npm-debug.log
Dockerfile
.dockerignore
.git
```

### 4. Security Practices

```dockerfile
# Use specific version, not latest
FROM node:20-alpine

# Use non-root user
RUN adduser -D appuser
USER appuser
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
```

## Common Commands

```bash
# Build image
docker build -t myapp:latest .

# Run container
docker run -d -p 3000:3000 myapp:latest

# View logs
docker logs -f <container_id>

# Enter container
docker exec -it <container_id> sh
```

## Summary

Following these best practices results in secure, efficient, and maintainable Docker images.
""",
    },
    {
        "title_zh": "Git 工作流完全指南",
        "title_en": "Complete Guide to Git Workflow",
        "category": "tutorial",
        "tags": ["git", "tools"],
        "code_language": "bash",
        "code_snippet": """# 初始化仓库
git init

# 配置用户信息
git config user.name "Your Name"
git config user.email "your@email.com"

# 创建分支
git checkout -b feature/new-feature

# 添加文件
git add .

# 提交更改
git commit -m "feat: add new feature"

# 推送到远程
git push origin feature/new-feature

# 合并分支
git checkout main
git merge --no-ff feature/new-feature

# 变基操作
git checkout feature/another-feature
git rebase main

# 解决冲突后继续变基
git add .
git rebase --continue

# 交互式变基（压缩提交）
git rebase -i HEAD~3

# Cherry-pick 特定提交
git cherry-pick abc123

# 暂存工作区
git stash
git stash pop

# 查看历史
git log --oneline --graph --all""",
        "content_zh": """# Git 工作流完全指南

Git 是现代软件开发必不可少的版本控制工具。本文详细介绍 Git 的各种工作流和高级用法。

## 基础概念

### 工作区、暂存区、仓库

- **工作区**：实际编辑文件的目录
- **暂存区**：准备提交的更改
- **仓库**：完整的版本历史

## 常用命令速查

```bash
{code}
```

## 分支策略

### Git Flow

```
main (生产分支)
  └── develop (开发分支)
        ├── feature/xxx (功能分支)
        ├── feature/yyy
        └── release/x.x (发布分支)
                  └── hotfix/xxx (热修复分支)
```

### GitHub Flow

更简单的流程：

1. 从 main 创建分支
2. 开发并提交
3. 创建 Pull Request
4. Code Review
5. 合并到 main

## Commit 规范

使用约定式提交：

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试
chore: 构建/工具
```

示例：

```
feat: 添加用户登录功能
fix: 修复登录验证错误
docs: 更新 API 文档
```

## 高级技巧

### 交互式变基

```bash
# 压缩最近 3 个提交
git rebase -i HEAD~3
```

### Cherry-pick

```bash
# 选择特定提交应用到当前分支
git cherry-pick abc123
```

### Stash

```bash
# 暂存当前工作
git stash

# 恢复暂存
git stash pop
```

## 最佳实践

1. **频繁提交**：小步快跑，便于回滚
2. **有意义的提交信息**：说明做了什么
3. **使用分支**：不要直接在 main 上开发
4. **定期同步**：保持与远程仓库同步
5. **Code Review**：合并前进行代码审查

## 总结

掌握 Git 工作流是团队协作的基础，选择适合团队的分支策略并坚持执行。
""",
        "content_en": """# Complete Guide to Git Workflow

Git is an essential version control tool for modern software development. This guide covers various Git workflows and advanced usage.

## Basic Concepts

### Working Directory, Staging Area, Repository

- **Working Directory**: Where you edit files
- **Staging Area**: Changes ready to commit
- **Repository**: Complete version history

## Common Commands

```bash
{code}
```

## Branching Strategies

### Git Flow

```
main (production)
  └── develop
        ├── feature/xxx
        └── release/x.x
```

### GitHub Flow

Simpler workflow:

1. Create branch from main
2. Develop and commit
3. Create Pull Request
4. Code Review
5. Merge to main

## Commit Convention

Use Conventional Commits:

```
feat: new feature
fix: bug fix
docs: documentation
style: formatting
refactor: code refactoring
test: tests
chore: build/tools
```

## Advanced Tips

### Interactive Rebase

```bash
git rebase -i HEAD~3
```

### Cherry-pick

```bash
git cherry-pick abc123
```

### Stash

```bash
git stash
git stash pop
```

## Best Practices

1. Commit frequently
2. Write meaningful messages
3. Use branches
4. Sync regularly
5. Code Review before merge

## Summary

Mastering Git workflow is fundamental for team collaboration.
""",
    },
    {
        "title_zh": "程序员的效率提升之道",
        "title_en": "Productivity Tips for Programmers",
        "category": "essay",
        "tags": [],
        "code_language": "",
        "code_snippet": "",
        "content_zh": """# 程序员的效率提升之道

作为一名程序员，如何在有限的时间内产出更多高质量的代码？这是每个人都在思考的问题。

## 时间管理

### 番茄工作法

25 分钟专注工作 + 5 分钟休息，每 4 个番茄后休息 15-30 分钟。

### 时间块

将一天划分为不同的时间块：

| 时间 | 活动 |
|------|------|
| 9:00-11:00 | 深度工作（复杂任务） |
| 11:00-12:00 | 会议、沟通 |
| 14:00-16:00 | 编码 |
| 16:00-17:00 | Code Review、学习 |

## 工具选择

### IDE 配置

- 熟练使用快捷键
- 安装提高效率的插件
- 配置代码片段

### 命令行技巧

```bash
# 使用 alias 简化命令
alias gs='git status'
alias gp='git push'
alias dc='docker-compose'

# 使用 zoxide 快速跳转
z myproject

# 使用 fzf 模糊搜索
Ctrl+R 搜索历史命令
```

## 学习方法

### 刻意练习

1. 明确目标
2. 专注练习
3. 获取反馈
4. 纠正改进

### 费曼学习法

1. 选择一个概念
2. 用简单语言解释它
3. 找出知识盲点
4. 简化和类比

## 健康习惯

### 身体健康

- 定时休息眼睛
- 保持正确坐姿
- 每天运动 30 分钟
- 充足睡眠

### 心理健康

- 学会说"不"
- 保持工作生活平衡
- 培养编程之外的爱好

## 总结

效率提升不是一蹴而就的，需要持续优化和调整。找到适合自己的方法，坚持下去。
""",
        "content_en": """# Productivity Tips for Programmers

As a programmer, how to produce more high-quality code in limited time? This is a question everyone thinks about.

## Time Management

### Pomodoro Technique

25 minutes focused work + 5 minutes break.

### Time Blocking

| Time | Activity |
|------|----------|
| 9:00-11:00 | Deep work |
| 11:00-12:00 | Meetings |
| 14:00-16:00 | Coding |
| 16:00-17:00 | Code Review |

## Tools

### IDE Setup

- Master keyboard shortcuts
- Install productivity plugins
- Configure code snippets

### Command Line Tips

```bash
# Use aliases
alias gs='git status'
alias gp='git push'

# Use zoxide for quick navigation
z myproject

# Use fzf for fuzzy search
Ctrl+R to search history
```

## Learning Methods

### Deliberate Practice

1. Clear goals
2. Focused practice
3. Get feedback
4. Correct and improve

### Feynman Technique

1. Choose a concept
2. Explain it simply
3. Find gaps
4. Simplify

## Health Habits

### Physical Health

- Rest your eyes regularly
- Maintain good posture
- Exercise 30 minutes daily
- Get enough sleep

### Mental Health

- Learn to say "no"
- Work-life balance
- Hobbies beyond coding

## Summary

Productivity improvement takes time. Find what works for you and stick with it.
""",
    },
]


def generate_slug(title: str) -> str:
    """生成 URL slug"""
    import re

    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


async def create_mock_data(
    num_posts: int = 20, num_users: int = 10, num_comments: int = 50
) -> None:
    """创建 Mock 数据"""
    async with async_session_maker() as session:
        print("🚀 开始创建 Mock 数据...\n")

        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                username="admin",
                email="admin@rosetta.dev",
                password_hash=get_password_hash("admin123"),
                nickname="Administrator",
                bio="系统管理员",
                is_active=True,
                is_staff=True,
                is_superuser=True,
            )
            session.add(admin)
            await session.flush()
            print("✓ 创建管理员: admin / admin123")

        categories_map: dict[str, Category] = {}
        for cat_data in CATEGORIES_DATA:
            result = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            category = result.scalar_one_or_none()

            if not category:
                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"],
                    color=cat_data["color"],
                    icon=cat_data["icon"],
                )
                session.add(category)
                await session.flush()
                print(f"✓ 创建分类: {cat_data['slug']}")

            categories_map[cat_data["slug"]] = category

        tags_map: dict[str, Tag] = {}
        for tag_data in TAGS_DATA:
            result = await session.execute(select(Tag).where(Tag.slug == tag_data["slug"]))
            tag = result.scalar_one_or_none()

            if not tag:
                tag = Tag(
                    name=tag_data["name"],
                    slug=tag_data["slug"],
                    color=tag_data["color"],
                    is_active=True,
                )
                session.add(tag)
                await session.flush()
                print(f"✓ 创建标签: {tag_data['slug']}")

            tags_map[tag_data["slug"]] = tag

        print(f"\n📝 创建 {len(ARTICLE_TEMPLATES)} 篇模板文章...")
        for template in ARTICLE_TEMPLATES:
            result = await session.execute(
                select(Post).where(Post.slug == generate_slug(template["title_zh"]))
            )
            post = result.scalar_one_or_none()

            if not post:
                category = categories_map.get(template["category"])
                tag_slugs = template.get("tags", [])
                tags = [tags_map[slug] for slug in tag_slugs if slug in tags_map]

                code = template.get("code_snippet", "")
                code_lang = template.get("code_language", "")

                content_zh = (
                    template["content_zh"]
                    .replace("{code}", code)
                    .replace("{code_language}", code_lang)
                )
                content_en = (
                    template["content_en"]
                    .replace("{code}", code)
                    .replace("{code_language}", code_lang)
                )

                post = Post(
                    title=create_multilang(template["title_zh"], template["title_en"]),
                    slug=generate_slug(template["title_zh"]),
                    content=create_multilang(content_zh, content_en),
                    excerpt=create_multilang(
                        template["title_zh"] + " - 详细教程和最佳实践",
                        template["title_en"] + " - Detailed tutorial and best practices",
                    ),
                    author_id=admin.id,
                    category_id=category.id if category else None,
                    status="published",
                    is_pinned=random.choice([True, False, False, False]),
                    allow_comments=True,
                    views=random.randint(100, 5000),
                    created_at=datetime.now() - timedelta(days=random.randint(1, 60)),
                    published_at=datetime.now() - timedelta(days=random.randint(1, 60)),
                )
                post.tags = tags
                session.add(post)
                print(f"  ✓ {template['title_zh']}")

        print(f"\n📝 创建 {num_posts} 篇随机文章...")
        for i in range(num_posts):
            title_zh = fake.sentence(nb_words=6)[:-1]
            title_en = fake_en.sentence(nb_words=6)[:-1]
            slug = generate_slug(f"{title_zh}-{i}")

            result = await session.execute(select(Post).where(Post.slug == slug))
            if result.scalar_one_or_none():
                continue

            category = random.choice(list(categories_map.values())) if categories_map else None
            tags = random.sample(list(tags_map.values()), k=random.randint(0, 3))

            paragraphs_zh = [fake.paragraph(nb_sentences=5) for _ in range(random.randint(3, 8))]
            paragraphs_en = [fake_en.paragraph(nb_sentences=5) for _ in range(len(paragraphs_zh))]

            content_zh = "\n\n".join(
                [f"## 第 {j + 1} 节\n\n{p}" for j, p in enumerate(paragraphs_zh)]
            )
            content_en = "\n\n".join(
                [f"## Section {j + 1}\n\n{p}" for j, p in enumerate(paragraphs_en)]
            )

            post = Post(
                title=create_multilang(title_zh, title_en),
                slug=slug,
                content=create_multilang(content_zh, content_en),
                excerpt=create_multilang(
                    paragraphs_zh[0][:100] if paragraphs_zh else "",
                    paragraphs_en[0][:100] if paragraphs_en else "",
                ),
                author_id=admin.id,
                category_id=category.id if category else None,
                status=random.choice(["published", "published", "published", "draft"]),
                is_pinned=False,
                allow_comments=True,
                views=random.randint(10, 2000),
                created_at=datetime.now() - timedelta(days=random.randint(1, 90)),
                published_at=datetime.now() - timedelta(days=random.randint(1, 90))
                if random.random() > 0.2
                else None,
            )
            post.tags = tags
            session.add(post)

        print(f"✓ 创建 {num_posts} 篇随机文章")

        print(f"\n👥 创建 {num_users} 个用户...")
        users = [admin]
        for i in range(num_users):
            username = fake.user_name() + str(i)
            result = await session.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none():
                continue

            user = User(
                username=username,
                email=fake.email(),
                password_hash=get_password_hash("password123"),
                nickname=fake.name(),
                bio=fake.sentence(),
                is_active=True,
                is_staff=False,
                is_superuser=False,
                created_at=datetime.now() - timedelta(days=random.randint(30, 365)),
            )
            session.add(user)
            users.append(user)
        print(f"✓ 创建 {num_users} 个用户")

        await session.flush()

        print(f"\n💬 创建 {num_comments} 条评论...")
        result = await session.execute(select(Post).where(Post.status == "published"))
        posts = list(result.scalars().all())

        for i in range(num_comments):
            if not posts:
                break
            post = random.choice(posts)
            user = random.choice(users)

            comment = Comment(
                post_id=post.id,
                user_id=user.id,
                author_name=user.nickname or user.username,
                author_email=user.email,
                content=fake.paragraph(nb_sentences=2),
                active=True,
                created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
            )
            session.add(comment)
        print(f"✓ 创建 {num_comments} 条评论")

        print("\n🔗 创建导航和友链...")
        # 清空旧导航
        await session.execute(Navigation.__table__.delete())
        await session.flush()

        # 先创建父导航，记录ID映射
        nav_flat: list[dict] = []
        # ===== 父级导航（parent_id=None） =====
        # 1. 首页
        nav_flat.append({
            "temp_id": "home",
            "parent_temp_id": None,
            "title": create_multilang("首页", "Home", "ホーム", "首頁"),
            "url": "/",
            "icon": "material-symbols:home",
            "order": 1,
        })
        # 2. 文章（父）
        nav_flat.append({
            "temp_id": "posts_parent",
            "parent_temp_id": None,
            "title": create_multilang("文章", "Posts", "投稿一覧", "文章"),
            "url": "#",
            "icon": "material-symbols:article",
            "order": 2,
        })
        # 3. 社交（父）
        nav_flat.append({
            "temp_id": "social_parent",
            "parent_temp_id": None,
            "title": create_multilang("社交", "Social", "ソーシャル", "社交"),
            "url": "#",
            "icon": "material-symbols:group",
            "order": 3,
        })
        # 4. 我的（父）
        nav_flat.append({
            "temp_id": "mine_parent",
            "parent_temp_id": None,
            "title": create_multilang("我的", "My", "マイページ", "我的"),
            "url": "#",
            "icon": "material-symbols:person",
            "order": 4,
        })
        # 5. 关于（父）
        nav_flat.append({
            "temp_id": "about_parent",
            "parent_temp_id": None,
            "title": create_multilang("关于", "About", "このサイトについて", "關於"),
            "url": "#",
            "icon": "material-symbols:info",
            "order": 5,
        })
        # ===== 子级导航 =====
        # 文章 -> 归档
        nav_flat.append({
            "temp_id": "archive",
            "parent_temp_id": "posts_parent",
            "title": create_multilang("归档", "Archive", "アーカイブ", "彙整"),
            "url": "/archive/",
            "icon": "material-symbols:archive",
            "order": 1,
        })
        # 文章 -> 分类
        nav_flat.append({
            "temp_id": "categories",
            "parent_temp_id": "posts_parent",
            "title": create_multilang("分类", "Categories", "カテゴリ", "分類"),
            "url": "/categories/",
            "icon": "material-symbols:folder-open-rounded",
            "order": 2,
        })
        # 文章 -> 标签
        nav_flat.append({
            "temp_id": "tags",
            "parent_temp_id": "posts_parent",
            "title": create_multilang("标签", "Tags", "タグ", "標籤"),
            "url": "/tags/",
            "icon": "material-symbols:tag-rounded",
            "order": 3,
        })
        # 社交 -> 友链
        nav_flat.append({
            "temp_id": "friends",
            "parent_temp_id": "social_parent",
            "title": create_multilang("友链", "Friends", "フレンド", "友鏈"),
            "url": "/friends/",
            "icon": "material-symbols:link-2-rounded",
            "order": 1,
        })
        # 社交 -> 留言板
        nav_flat.append({
            "temp_id": "guestbook",
            "parent_temp_id": "social_parent",
            "title": create_multilang("留言板", "Guestbook", "掲示板", "留言板"),
            "url": "/guestbook/",
            "icon": "material-symbols:chat",
            "order": 2,
        })
        # 我的 -> 动态
        nav_flat.append({
            "temp_id": "dynamic",
            "parent_temp_id": "mine_parent",
            "title": create_multilang("动态", "Dynamic", "ダイナミック", "動態"),
            "url": "/dynamic/",
            "icon": "material-symbols:forum-rounded",
            "order": 1,
        })
        # 我的 -> 相册
        nav_flat.append({
            "temp_id": "gallery",
            "parent_temp_id": "mine_parent",
            "title": create_multilang("相册", "Gallery", "ギャラリー", "相簿"),
            "url": "/gallery/",
            "icon": "material-symbols:photo-library",
            "order": 2,
        })
        # 我的 -> 后台管理
        nav_flat.append({
            "temp_id": "admin",
            "parent_temp_id": "mine_parent",
            "title": create_multilang("后台管理", "Admin", "管理画面", "後台管理"),
            "url": "/admin/",
            "icon": "material-symbols:dashboard",
            "order": 3,
        })
        # 关于 -> 打赏
        nav_flat.append({
            "temp_id": "sponsor",
            "parent_temp_id": "about_parent",
            "title": create_multilang("打赏", "Sponsor", "スポンサー", "打賞"),
            "url": "/sponsor/",
            "icon": "material-symbols:favorite",
            "order": 1,
        })
        # 关于 -> 关于我
        nav_flat.append({
            "temp_id": "about_me",
            "parent_temp_id": "about_parent",
            "title": create_multilang("关于我", "About Me", "私について", "關於我"),
            "url": "/about/",
            "icon": "material-symbols:person",
            "order": 2,
        })

        # 两阶段创建：先创建所有导航，再根据 temp_id 映射设置 parent_id
        temp_to_db_id: dict[str, int] = {}
        # 阶段1：创建所有导航（不设置parent_id）
        for item in nav_flat:
            nav = Navigation(
                title=item["title"],
                url=item["url"],
                icon=item["icon"],
                order=item["order"],
                location="header",
                is_active=True,
                target_blank=False,
                parent_id=None,
            )
            session.add(nav)
            await session.flush()  # 立即获取ID
            temp_to_db_id[item["temp_id"]] = nav.id

        # 阶段2：更新所有导航的parent_id
        for item in nav_flat:
            if item["parent_temp_id"] and item["parent_temp_id"] in temp_to_db_id:
                nav_id = temp_to_db_id[item["temp_id"]]
                parent_id = temp_to_db_id[item["parent_temp_id"]]
                result = await session.execute(select(Navigation).where(Navigation.id == nav_id))
                nav_obj = result.scalar_one_or_none()
                if nav_obj:
                    nav_obj.parent_id = parent_id

        await session.flush()
        print("✓ 创建导航菜单（含父子结构）")

        friend_links = [
            {
                "name": create_multilang("GitHub", "GitHub"),
                "url": "https://github.com",
                "logo": "https://github.githubassets.com/favicons/favicon.svg",
            },
            {
                "name": create_multilang("Vue.js", "Vue.js"),
                "url": "https://vuejs.org",
                "logo": "https://vuejs.org/logo.svg",
            },
            {
                "name": create_multilang("FastAPI", "FastAPI"),
                "url": "https://fastapi.tiangolo.com",
                "logo": "https://fastapi.tiangolo.com/img/favicon.png",
            },
        ]

        for link in friend_links:
            result = await session.execute(select(FriendLink).where(FriendLink.url == link["url"]))
            if not result.scalar_one_or_none():
                fl = FriendLink(
                    name=link["name"], url=link["url"], logo=link.get("logo", ""), is_active=True
                )
                session.add(fl)
        print("✓ 创建友情链接")

        print("\n💬 创建网站动态（说说）...")
        activity_contents = [
            {
                "zh": "今天天气真好，写了一篇关于 Python 异步编程的文章，欢迎大家阅读讨论～",
                "en": "Great weather today! Just published an article about Python async programming. Feel free to read and discuss~",
                "ja": "今日はいい天気ですね！Python 非同期プログラミングについての記事を投稿しました。ぜひ読んで議論してください〜",
                "zh_Hant": "今天天氣真好，寫了一篇關於 Python 異步編程的文章，歡迎大家閱讀討論～",
            },
            {
                "zh": "新功能上线：全站支持多语言切换啦！现在可以在简体中文、繁体中文、英文、日文之间自由切换。",
                "en": "New feature: Full multi-language support! Now you can freely switch between Simplified Chinese, Traditional Chinese, English, and Japanese.",
                "ja": "新機能リリース：サイト全体で多言語切り替えに対応！簡体字中国語、繁体字中国語、英語、日本語の間で自由に切り替えられます。",
                "zh_Hant": "新功能上線：全站支援多語言切換啦！現在可以在簡體中文、繁體中文、英文、日文之間自由切換。",
            },
            {
                "zh": "周末把博客的 UI 全部翻新了一遍，采用了青蓝色调的设计风格，大家觉得怎么样？",
                "en": "Redesigned the entire blog UI this weekend with a cyan-blue color palette. What do you all think?",
                "ja": "週末にブログの UI を全面リニューアルしました。シアンブルーを基調としたデザインにしたのですが、皆さんどう思いますか？",
                "zh_Hant": "週末把部落格的 UI 全部翻新了一遍，採用了青藍色調的設計風格，大家覺得怎麼樣？",
            },
            {
                "zh": "刚看完《代码整洁之道》，收获满满。强烈推荐每个程序员都读一遍！",
                "en": "Just finished reading \"Clean Code\". Gained so much insight. Highly recommend every programmer to read it!",
                "ja": "「クリーンコード」を読み終わったばかりで、非常に勉強になりました。すべてのプログラマーに強くお勧めします！",
                "zh_Hant": "剛看完《程式碼整潔之道》，收穫滿滿。強烈推薦每個程式設計師都讀一遍！",
            },
            {
                "zh": "最近在研究 WebAssembly，准备写一篇入门教程，敬请期待～",
                "en": "Recently been studying WebAssembly. Planning to write a beginner tutorial. Stay tuned~",
                "ja": "最近 WebAssembly を勉強しています。入門チュートリアルを書く予定ですので、お楽しみに〜",
                "zh_Hant": "最近在研究 WebAssembly，準備寫一篇入門教學，敬請期待～",
            },
            {
                "zh": "修复了一个困扰两天的 bug，原因竟然是少写了一个 await。😭 异步编程一定要细心啊！",
                "en": "Fixed a bug that haunted me for two days. Turns out I just forgot an `await`. 😭 Gotta be careful with async code!",
                "ja": "2 日間悩まされたバグを修正しました。原因はなんと `await` を一つ書き忘れていただけでした。😭 非同期コードは慎重に書かないと！",
                "zh_Hant": "修復了一個困擾兩天的 bug，原因竟然是少寫了一個 await。😭 異步程式設計一定要細心啊！",
            },
            {
                "zh": "分享一个小技巧：写代码前先写注释，再填充实现，这样逻辑会清晰很多。",
                "en": "Quick tip: Write comments first before writing the actual code. This makes the logic much clearer!",
                "ja": "ちょっとしたテクニック：実装を書く前にまずコメントを書くと、ロジックがずっと明確になります。",
                "zh_Hant": "分享一個小技巧：寫程式碼前先寫註解，再填充實現，這樣邏輯會清晰很多。",
            },
            {
                "zh": "周末愉快！今天去爬山了，呼吸了新鲜空气，下周精力满满！⛰️",
                "en": "Happy weekend! Went hiking today, breathed some fresh air, feeling energized for next week! ⛰️",
                "ja": "週末を楽しんで！今日は山登りに行って新鮮な空気を吸いました。来週は元気いっぱいです！⛰️",
                "zh_Hant": "週末愉快！今天去爬山了，呼吸了新鮮空氣，下週精力滿滿！⛰️",
            },
        ]
        activity_types = ["say", "say", "say", "say", "article", "update", "notice", "say"]
        for idx, content in enumerate(activity_contents):
            created = datetime.now() - timedelta(
                days=random.randint(0, 20),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            act = Activity(
                content=content,
                type=activity_types[idx % len(activity_types)],
                author_id=admin.id,
                is_published=True,
                created_at=created,
                updated_at=created,
            )
            session.add(act)
        print(f"✓ 创建 {len(activity_contents)} 条网站动态")

        # ===== 网站公告 =====
        await session.execute(Announcement.__table__.delete())
        await session.flush()
        announcement_list = [
            {
                "title": "🎉 网站全新改版上线！",
                "content": "感谢大家一直以来的支持，本站已全面升级改版！新增了动态API、文章分类、标签云等功能，优化了页面加载速度和响应式布局。欢迎体验新功能！",
                "type": "success",
                "is_active": True,
                "is_dismissible": True,
                "start_time": datetime.now(UTC) - timedelta(days=1),
                "end_time": None,
                "sort_order": 1,
            },
            {
                "title": "📢 友情链接招募中",
                "content": "本站现开放友情链接申请，欢迎同类技术博客、个人站点前来交换友链。请在留言板或邮件联系我，让我们一起互相引流！",
                "type": "info",
                "is_active": True,
                "is_dismissible": True,
                "start_time": None,
                "end_time": None,
                "sort_order": 2,
            },
            {
                "title": "⚠️ 服务器临时维护通知",
                "content": "本站将于本周六凌晨2:00-4:00进行服务器例行维护，期间站点可能无法访问，给您带来的不便敬请谅解。",
                "type": "warning",
                "is_active": True,
                "is_dismissible": False,
                "start_time": datetime.now(UTC) - timedelta(hours=2),
                "end_time": datetime.now(UTC) + timedelta(days=30),
                "sort_order": 3,
            },
        ]
        for ann_data in announcement_list:
            ann = Announcement(**ann_data)
            session.add(ann)
        await session.flush()
        print(f"✓ 创建 {len(announcement_list)} 条网站公告")

        await session.commit()

        print("\n" + "=" * 50)
        print("✅ Mock 数据创建完成！")
        print("=" * 50)
        print("\n📋 登录信息:")
        print("   用户名: admin")
        print("   密码: admin123")
        print("\n🌐 启动服务:")
        print("   python start.py --dev")


async def generate_all_mock_data(
    db,
    posts_count: int = 20,
    categories_count: int = 5,
    tags_count: int = 10,
    users_count: int = 5,
    comments_count: int = 50,
    reset: bool = False,
) -> dict:
    """生成模拟数据（供 API 调用）"""
    import random

    from backend.core.auth import get_password_hash
    from backend.models.blog import Category, Comment, Post, Tag
    from backend.models.user import User

    if reset:
        await db.execute(Comment.__table__.delete())
        await db.execute(Post.__table__.delete())
        await db.execute(Category.__table__.delete())
        await db.execute(Tag.__table__.delete())
        await db.execute(User.__table__.delete().where(User.__table__.c.username != "admin"))

    admin_result = await db.execute(select(User).where(User.username == "admin"))
    admin = admin_result.scalar_one_or_none()
    if not admin:
        admin = User(
            username="admin",
            email="admin@rosetta.dev",
            password_hash=get_password_hash("admin123"),
            nickname="Administrator",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        db.add(admin)
        await db.flush()

    categories = []
    cat_names = [
        ("技术", "Technology", "技術", "技術"),
        ("生活", "Life", "生活", "生活"),
        ("随笔", "Essay", "随筆", "隨筆"),
        ("教程", "Tutorial", "チュートリアル", "教學"),
        ("分享", "Share", "共有", "分享"),
        ("读书", "Books", "読書", "讀書"),
        ("旅行", "Travel", "旅行", "旅行"),
    ]
    for i in range(min(categories_count, len(cat_names))):
        zh, en, ja, tw = cat_names[i]
        slug = f"category-{i + 1}"
        cat = Category(
            name={"zh": zh, "en": en, "ja": ja, "zh_Hant": tw},
            slug=slug,
            description={
                "zh": f"{zh}分类",
                "en": f"{en} category",
                "ja": f"{ja}カテゴリ",
                "zh_Hant": f"{tw}分類",
            },
            color="primary",
        )
        db.add(cat)
        categories.append(cat)
    await db.flush()

    tags = []
    tag_names = [
        "Python",
        "JavaScript",
        "Vue",
        "React",
        "FastAPI",
        "Astro",
        "AI",
        "Docker",
        "Linux",
        "设计",
        "前端",
        "后端",
        "全栈",
        "数据库",
        "缓存",
        "安全",
        "性能",
        "测试",
        "DevOps",
        "云原生",
    ]
    for i in range(min(tags_count, len(tag_names))):
        name = tag_names[i]
        tag = Tag(
            name={"zh": name, "en": name, "ja": name, "zh_Hant": name},
            slug=f"tag-{i + 1}",
            color=f"#{random.randint(0x333333, 0xCCCCCC):06x}",
        )
        db.add(tag)
        tags.append(tag)
    await db.flush()

    users = []
    user_names = [
        "alice",
        "bob",
        "charlie",
        "david",
        "eva",
        "frank",
        "grace",
        "henry",
        "ivy",
        "jack",
    ]
    for i in range(min(users_count, len(user_names))):
        uname = user_names[i]
        u = User(
            username=uname,
            email=f"{uname}@example.com",
            password_hash=get_password_hash("password123"),
            nickname=uname.capitalize(),
            is_active=True,
        )
        db.add(u)
        users.append(u)
    await db.flush()

    posts = []
    titles_zh = [
        "深入理解Python异步编程",
        "JavaScript ES2024新特性详解",
        "Vue3组合式API最佳实践",
        "FastAPI高性能后端开发指南",
        "Docker容器化部署实战",
        "人工智能在软件开发中的应用",
        "微服务架构设计原则",
        "数据库性能优化技巧",
        "前端工程化实践",
        "Linux命令行技巧",
        "响应式设计原理与实现",
        "RESTful API设计规范",
        "缓存策略与Redis应用",
        "Web安全防护指南",
        "自动化测试最佳实践",
        "CI/CD流水线搭建",
        "TypeScript高级类型编程",
        "GraphQL vs REST对比",
        "PWA渐进式Web应用",
        "WebAssembly入门教程",
    ]
    titles_en = [
        "Deep Dive into Python Async Programming",
        "JavaScript ES2024 New Features",
        "Vue3 Composition API Best Practices",
        "FastAPI High Performance Backend Guide",
        "Docker Container Deployment",
        "AI in Software Development",
        "Microservices Architecture Design",
        "Database Performance Optimization",
        "Frontend Engineering Practice",
        "Linux Command Line Tips",
        "Responsive Design Principles",
        "RESTful API Design",
        "Caching Strategy with Redis",
        "Web Security Guide",
        "Automated Testing Best Practices",
        "CI/CD Pipeline Setup",
        "TypeScript Advanced Types",
        "GraphQL vs REST",
        "PWA Progressive Web Apps",
        "WebAssembly Tutorial",
    ]
    for i in range(min(posts_count, len(titles_zh))):
        cat = random.choice(categories) if categories else None
        post_tags = random.sample(tags, min(3, len(tags))) if tags else []
        author = random.choice(users) if users else admin
        content_zh = f"# {titles_zh[i]}\n\n这是第{i + 1}篇文章的内容。在这里我们将深入探讨{titles_zh[i]}的相关话题...\n\n## 概述\n\n本文详细介绍了{titles_zh[i]}的基本概念和实践方法...\n\n## 实践\n\n通过实际案例，我们学习了如何应用这些知识..."
        content_en = f"# {titles_en[i]}\n\nThis is the content of article {i + 1}. Here we will dive into {titles_en[i]}...\n\n## Overview\n\nThis article introduces the basic concepts of {titles_en[i]}...\n\n## Practice\n\nThrough real examples, we learn how to apply this knowledge..."
        p = Post(
            title={
                "zh": titles_zh[i],
                "en": titles_en[i],
                "ja": titles_zh[i],
                "zh_Hant": titles_zh[i],
            },
            slug=f"post-{i + 1}",
            excerpt={"zh": f"{titles_zh[i]}的摘要内容...", "en": f"Summary of {titles_en[i]}..."},
            content={"zh": content_zh, "en": content_en, "ja": content_zh, "zh_Hant": content_zh},
            category_id=cat.id if cat else None,
            author_id=author.id,
            status="published" if random.random() > 0.2 else "draft",
            views=random.randint(0, 5000),
        )
        if post_tags:
            p.tags = post_tags
        db.add(p)
        posts.append(p)
    await db.flush()

    comment_authors = users + [admin] if users else [admin]
    created_comments = 0
    for p in posts[: min(comments_count, len(posts))]:
        if not comment_authors:
            break
        num_comments = min(random.randint(1, 5), comments_count - created_comments)
        for j in range(num_comments):
            if created_comments >= comments_count:
                break
            ca = random.choice(comment_authors)
            c = Comment(
                post_id=p.id,
                user_id=ca.id,
                author_name=ca.nickname or ca.username,
                author_email=ca.email,
                content=f"这是对《{p.title.get('zh', '')}》的第{j + 1}条评论。写得很好！",
                active=random.random() > 0.1,
            )
            db.add(c)
            created_comments += 1

    await db.commit()

    return {
        "posts": len(posts),
        "categories": len(categories),
        "tags": len(tags),
        "users": len(users),
        "comments": created_comments,
    }


async def generate_oobe_mock_data(db, admin_id: int) -> dict:
    """生成 OOBE 阶段的真实种子数据：
    8 分类 + 24 标签 + 32 篇四语言真实技术文章（含代码块/对比表格）+ 真实感评论 + 25 条动态说说 + 示例留言板

    Args:
        db: 数据库会话
        admin_id: 已创建的管理员用户 ID

    Returns:
        dict: 各类型创建数量
    """
    import random
    from datetime import timedelta as _td

    from backend.models.activity import Activity
    from backend.models.blog import Category, Comment, Post, Tag

    # ---------- 加载种子数据 ----------
    try:
        from backend.scripts.oobe_seed_data import (
            ACTIVITY_TEMPLATES,
            ARTICLE_TEMPLATES_V3,
            COMMENT_CONTENT_TEMPLATES,
            COMMENT_PERSONAS,
            OOBE_CATEGORIES,
            OOBE_TAGS,
        )
    except Exception as _exc:  # noqa: BLE001
        import logging as _logging
        _logging.getLogger(__name__).warning("oobe_seed_data 导入失败，fallback 到最小数据: %s", _exc)
        return await generate_oobe_mock_data_minimal(db, admin_id)

    rng = random.Random(20250101)
    utc_now = datetime.now(UTC)

    # ---------- 1. 创建 8 个分类 ----------
    cat_map: dict[str, Category] = {}
    created_cats = 0
    for cat_data in OOBE_CATEGORIES:
        slug = cat_data["slug"]
        result = await db.execute(select(Category).where(Category.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            cat_map[slug] = existing
            continue
        # icon 规范化：自动补 heroicons: 前缀
        icon = cat_data.get("icon") or "heroicons:code-bracket"
        if ":" not in icon:
            icon = f"heroicons:{icon}"
        cat = Category(
            name=dict(cat_data["name"]),
            slug=slug,
            description=dict(cat_data["description"]),
            color=cat_data.get("color") or "#3B82F6",
            icon=icon,
        )
        db.add(cat)
        cat_map[slug] = cat
        created_cats += 1
    await db.flush()

    # ---------- 2. 创建 24 个标签 ----------
    tag_map: dict[str, Tag] = {}
    created_tags = 0
    for tag_data in OOBE_TAGS:
        slug = tag_data["slug"]
        result = await db.execute(select(Tag).where(Tag.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            tag_map[slug] = existing
            continue
        t = Tag(
            name=dict(tag_data["name"]),
            slug=slug,
            color=tag_data.get("color") or "#6366F1",
            is_active=True,
        )
        db.add(t)
        tag_map[slug] = t
        created_tags += 1
    await db.flush()

    # ---------- 3. 创建 32 篇四语言真实文章 ----------
    created_posts = 0
    created_views = 0
    post_cat_bucket: dict[int, str] = {}  # post_id -> bucket name for comments
    post_ids: list[int] = []

    for idx, art in enumerate(ARTICLE_TEMPLATES_V3):
        title_zh = (art.get("title_zh") or f"Article {idx+1}").strip()
        # slug = slugify 中英混合简化版（避免额外依赖）
        base_slug = art.get("slug") or (
            f"post-{idx+1}-{''.join(c for c in title_zh[:10] if c.isalnum())}".strip("-")
        )
        # 去重：循环探测直到 slug 可用（重复安装/重置重装场景下 -01 也会冲突）
        slug_candidate = base_slug or f"article-{idx+1}"
        probe = slug_candidate
        counter = 1
        while True:
            dup_row = (
                await db.execute(select(Post.id).where(Post.slug == probe).limit(1))
            ).scalar_one_or_none()
            if dup_row is None:
                break
            probe = f"{slug_candidate}-{counter:02d}"
            counter += 1
        slug_candidate = probe

        cat_obj = None
        cat_slug = art.get("category_slug") or "technology"
        cat_obj = cat_map.get(cat_slug) or next(iter(cat_map.values()), None)
        bucket = _cat_to_comment_bucket(cat_slug)
        post_cat_bucket[created_posts] = bucket

        tag_objs = []
        for ts in (art.get("tag_slugs") or []):
            if ts in tag_map:
                tag_objs.append(tag_map[ts])
        if not tag_objs and tag_map:
            # fallback 2 个随机标签
            tag_objs = rng.sample(list(tag_map.values()), k=min(2, len(tag_map)))

        excerpt_zh = (art.get("excerpt_zh") or title_zh).strip()
        excerpt_en = (art.get("excerpt_en") or excerpt_zh).strip()
        excerpt_ja = (art.get("excerpt_ja") or excerpt_zh).strip()
        excerpt_zh_hant = (art.get("excerpt_zh_hant") or excerpt_zh).strip()

        content_zh = (art.get("content_zh") or f"# {title_zh}\n\n{excerpt_zh}\n").strip()
        content_en = (art.get("content_en") or content_zh).strip()
        # ja/zh_Hant fallback：缺失时用对应语言的摘要+正文内容作为降级
        content_ja = art.get("content_ja") or _translate_fallback_ja(content_zh, content_en, title_zh)
        content_zh_hant = art.get("content_zh_hant") or _trad_fallback(content_zh)

        # 发布时间：按 idx 倒序分布（新→旧，跨度 45 天）
        days_ago = int((len(ARTICLE_TEMPLATES_V3) - idx - 1) * (45 / max(1, len(ARTICLE_TEMPLATES_V3))))
        hours_offset = rng.randint(0, 23)
        published_at = utc_now - _td(days=days_ago, hours=hours_offset)
        views = rng.randint(15, 480) + (32 - idx) * 6

        post = Post(
            title={
                "zh": title_zh,
                "en": (art.get("title_en") or title_zh).strip(),
                "ja": (art.get("title_ja") or title_zh).strip(),
                "zh_Hant": (art.get("title_zh_hant") or title_zh).strip(),
            },
            slug=slug_candidate,
            source="原创",
            excerpt={
                "zh": excerpt_zh,
                "en": excerpt_en,
                "ja": excerpt_ja,
                "zh_Hant": excerpt_zh_hant,
            },
            content={
                "zh": content_zh,
                "en": content_en,
                "ja": content_ja,
                "zh_Hant": content_zh_hant,
            },
            cover_image=None,
            author_id=int(admin_id),
            category_id=cat_obj.id if cat_obj else None,
            status="published",
            visibility="public",
            views=views,
            is_pinned=(idx == 0),  # 第 1 篇置顶
            allow_comments=True,
            meta_title={
                "zh": title_zh,
                "en": (art.get("title_en") or title_zh).strip(),
            },
            meta_description={
                "zh": excerpt_zh,
                "en": excerpt_en,
            },
            meta_keywords={
                "zh": ",".join([t.name.get("zh", "") for t in tag_objs[:5]]),
            },
            published_at=published_at,
            created_at=published_at,
            updated_at=published_at,
        )
        if tag_objs:
            post.tags = tag_objs
        db.add(post)
        created_posts += 1
        created_views += views
        await db.flush()
        post_ids.append(post.id)

    # ---------- 4. 生成真实感评论：每篇 3-7 条，约 160 条 ----------
    created_comments = 0
    root_comments_by_post: dict[int, list[Comment]] = {}
    try:
        for post_idx, pid in enumerate(post_ids):
            bucket = post_cat_bucket.get(post_idx, "backend")
            templates = COMMENT_CONTENT_TEMPLATES.get(bucket, COMMENT_CONTENT_TEMPLATES["backend"])
            num = rng.randint(3, 7)
            # 从人物库里随机不重复采样
            n_sample = min(num, len(COMMENT_PERSONAS))
            personas_sel = rng.sample(COMMENT_PERSONAS, k=n_sample)
            tmpl_sel = rng.sample(templates, k=min(num, len(templates)))
            if len(tmpl_sel) < num:
                tmpl_sel += rng.choices(templates, k=num - len(tmpl_sel))

            base_published = utc_now - _td(days=rng.randint(1, 30))
            roots_for_post: list[Comment] = []
            for i, (persona, tmpl_text) in enumerate(zip(personas_sel, tmpl_sel)):
                created = base_published + _td(hours=rng.randint(1, 48), minutes=rng.randint(0, 59))
                status = "approved"
                active = True
                if rng.random() < 0.10:  # 10% pending
                    status = "pending"
                    active = False
                likes = rng.randint(0, 18)

                comment = Comment(
                    post_id=pid,
                    user_id=None,
                    parent_id=None,
                    author_name=str(persona["nickname"]),
                    author_email=(persona.get("email") or None),
                    author_website=(persona.get("website") or None),
                    author_ip=str(persona.get("ip_range") or "10.0.0.x"),
                    author_user_agent=(persona.get("user_agent") or None),
                    qq=(persona.get("qq") or None),
                    github=(persona.get("github") or None),
                    avatar_source=str(persona.get("avatar_source") or "auto"),
                    content=str(tmpl_text),
                    status=status,
                    active=active,
                    likes_count=likes,
                    is_pinned=False,
                    created_at=created,
                    updated_at=created,
                )
                db.add(comment)
                roots_for_post.append(comment)
                created_comments += 1
            await db.flush()
            root_comments_by_post[pid] = roots_for_post

            # 约 35% 的根评论有 1-2 条嵌套回复
            for rc in roots_for_post:
                if rng.random() < 0.35 and rc.status == "approved":
                    n_rep = rng.randint(1, 2)
                    for _ in range(n_rep):
                        if not COMMENT_PERSONAS:
                            break
                        rp = rng.choice(COMMENT_PERSONAS)
                        tmpl_pool = COMMENT_CONTENT_TEMPLATES.get(bucket, COMMENT_CONTENT_TEMPLATES["backend"])
                        txt = rng.choice(tmpl_pool)
                        reply_at = rc.created_at + _td(hours=rng.randint(1, 15), minutes=rng.randint(1, 59))
                        reply_status = "approved" if rng.random() < 0.92 else "pending"
                        is_admin_reply = rng.random() < 0.22  # 约 22% 由管理员回复
                        if is_admin_reply:
                            r_author_name = "Choyeon"
                            r_author_email = "choyeon@foxmail.com"
                            r_author_website = "https://rosetta.choyeon.cc"
                            r_author_ip = "127.0.0.1"
                            r_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
                            r_qq = None
                            r_gh = None
                            r_avatar_src = "github"
                            r_user_id = int(admin_id)
                        else:
                            r_author_name = str(rp["nickname"])
                            r_author_email = rp.get("email") or None
                            r_author_website = rp.get("website") or None
                            r_author_ip = str(rp.get("ip_range") or "10.0.0.x")
                            r_ua = rp.get("user_agent") or None
                            r_qq = rp.get("qq") or None
                            r_gh = rp.get("github") or None
                            r_avatar_src = str(rp.get("avatar_source") or "auto")
                            r_user_id = None
                        reply = Comment(
                            post_id=pid,
                            user_id=r_user_id,
                            parent_id=rc.id,
                            author_name=r_author_name,
                            author_email=r_author_email,
                            author_website=r_author_website,
                            author_ip=r_author_ip,
                            author_user_agent=r_ua,
                            qq=r_qq,
                            github=r_gh,
                            avatar_source=r_avatar_src,
                            content=str(txt),
                            status=reply_status,
                            active=(reply_status == "approved"),
                            likes_count=rng.randint(0, 8),
                            is_pinned=False,
                            created_at=reply_at,
                            updated_at=reply_at,
                        )
                        db.add(reply)
                        created_comments += 1
            await db.flush()
    except Exception as exc:  # noqa: BLE001
        import logging as _logging
        _logging.getLogger(__name__).warning("OOBE comments 生成失败（降级）: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    # ---------- 5. 生成 25 条四语言动态说说 ----------
    created_activities = 0
    try:
        n_act = min(25, len(ACTIVITY_TEMPLATES))
        for a_idx in range(n_act):
            tpl = ACTIVITY_TEMPLATES[a_idx]
            days_a = rng.randint(0, 40)
            hr_a = rng.randint(0, 23)
            mn_a = rng.randint(0, 59)
            at = utc_now - _td(days=days_a, hours=hr_a, minutes=mn_a)
            act_type = str(tpl.get("type") or "say")[:20]
            act = Activity(
                content={
                    "zh": str(tpl.get("zh") or "").strip(),
                    "en": str(tpl.get("en") or tpl.get("zh") or "").strip(),
                    "ja": str(tpl.get("ja") or tpl.get("zh") or "").strip(),
                    "zh_Hant": str(tpl.get("zh_Hant") or tpl.get("zh") or "").strip(),
                },
                type=act_type,
                author_id=int(admin_id),
                is_published=True,
                likes_count=rng.randint(0, 36),
                created_at=at,
                updated_at=at,
            )
            db.add(act)
            created_activities += 1
        await db.flush()
    except Exception as exc:  # noqa: BLE001
        import logging as _logging
        _logging.getLogger(__name__).warning("OOBE activities 生成失败（降级）: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    # ---------- 6. 生成 8 条真实感留言板 ----------
    created_guestbook = 0
    try:
        created_guestbook = await _oobe_create_enhanced_guestbook(db, admin_id, COMMENT_PERSONAS, utc_now, rng)
    except Exception as exc:  # noqa: BLE001
        import logging as _logging
        _logging.getLogger(__name__).warning("OOBE guestbook 生成失败（降级）: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass

    await db.commit()

    return {
        "categories": created_cats,
        "tags": created_tags,
        "posts": created_posts,
        "comments": created_comments,
        "activities": created_activities,
        "guestbook_entries": created_guestbook,
        "views": created_views,
    }


def _cat_to_comment_bucket(cat_slug: str) -> str:
    """文章分类 slug → 评论模板 bucket"""
    mapping = {
        "backend": "backend",
        "database": "database",
        "devops": "devops",
        "tools": "devops",
        "ai": "ai",
        "frontend": "frontend",
        "tutorial": "backend",
        "technology": "backend",
        "fullstack": "frontend",
        "essays": "backend",
        "translation": "backend",
        "lifestyle": "backend",
    }
    return mapping.get(cat_slug, "backend")


def _trad_fallback(zh_text: str) -> str:
    """繁体 fallback：直接复用简体（避免引入额外 opencc 依赖），保留原 Markdown 结构。"""
    return zh_text


def _translate_fallback_ja(zh_text: str, en_text: str, title_zh: str) -> str:
    """日文 fallback：优先返回 en 内容（日文环境用户至少能读英文技术文档），否则返回 zh。"""
    return en_text or zh_text


async def generate_oobe_mock_data_minimal(db, admin_id: int) -> dict:
    """当 oobe_seed_data 模块缺失时的最小兼容 fallback（与旧版 generate_oobe_mock_data 行为保持一致）。"""
    from backend.models.blog import Category, Post, Tag

    created_cats = 0
    oobe_categories = [
        {
            "name": {"zh": "技术", "en": "Technology", "ja": "技術", "zh_Hant": "技術"},
            "slug": "technology",
            "description": {
                "zh": "技术相关文章",
                "en": "Technology related articles",
                "ja": "技術関連の記事",
                "zh_Hant": "技術相關文章",
            },
            "color": "#3B82F6",
            "icon": "heroicons:code-bracket",
        },
    ]
    tech_category = None
    for cat_data in oobe_categories:
        result = await db.execute(select(Category).where(Category.slug == cat_data["slug"]))
        existing = result.scalar_one_or_none()
        if existing:
            if cat_data["slug"] == "technology":
                tech_category = existing
            continue
        cat = Category(**cat_data)
        db.add(cat)
        created_cats += 1
        if cat_data["slug"] == "technology":
            tech_category = cat
    await db.flush()

    created_tags = 0
    oobe_tags = [
        {"name": {"zh": "Python", "en": "Python", "ja": "Python", "zh_Hant": "Python"}, "slug": "python", "color": "#3776AB"},
        {"name": {"zh": "JavaScript", "en": "JavaScript", "ja": "JavaScript", "zh_Hant": "JavaScript"}, "slug": "javascript", "color": "#F7DF1E"},
        {"name": {"zh": "Vue", "en": "Vue", "ja": "Vue", "zh_Hant": "Vue"}, "slug": "vue", "color": "#4FC08D"},
    ]
    tag_objs = []
    for tag_data in oobe_tags:
        result = await db.execute(select(Tag).where(Tag.slug == tag_data["slug"]))
        t = result.scalar_one_or_none()
        if not t:
            t = Tag(**tag_data, is_active=True)
            db.add(t)
            created_tags += 1
        tag_objs.append(t)
    await db.flush()

    created_posts = 0
    hello_slug = "hello-world-oobe"
    result = await db.execute(select(Post).where(Post.slug == hello_slug))
    hello_post = result.scalar_one_or_none()
    if not hello_post:
        hello_content_zh = "# Hello World\n\n欢迎使用 **Rosetta** 博客平台！\n\n" \
                           "这是最小化种子数据生成的示例文章。\n\n## 下一步\n\n" \
                           "1. 访问管理后台撰写真实文章\n2. 在站点设置中修改网站名称与描述\n\n祝写作愉快！\n"
        hello_post = Post(
            title={"zh": "Hello World", "en": "Hello World", "ja": "Hello World", "zh_Hant": "Hello World"},
            slug=hello_slug,
            excerpt={"zh": "欢迎使用 Rosetta 博客平台！", "en": "Welcome to Rosetta!"},
            content={
                "zh": hello_content_zh,
                "en": hello_content_zh,
                "ja": hello_content_zh,
                "zh_Hant": hello_content_zh,
            },
            author_id=admin_id,
            category_id=tech_category.id if tech_category else None,
            status="published",
            allow_comments=True,
            is_pinned=False,
            views=12,
            published_at=datetime.now(UTC),
        )
        if tag_objs:
            hello_post.tags = tag_objs
        db.add(hello_post)
        created_posts += 1
        await db.flush()

    created_guestbook = 0
    try:
        created_guestbook = await create_sample_guestbook_entries(db, admin_id)
    except Exception:
        created_guestbook = 0

    await db.commit()
    return {
        "categories": created_cats,
        "tags": created_tags,
        "posts": created_posts,
        "comments": 0,
        "activities": 0,
        "guestbook_entries": created_guestbook,
    }


async def _oobe_create_enhanced_guestbook(db, admin_id: int, personas: list, utc_now, rng) -> int:
    """基于真实人物库生成 8 条留言板（1管理员置顶 + 5游客 + 1精华 + 1 pending + 1 管理员回复）"""
    from backend.models.guestbook import GuestbookEntry

    result = await db.execute(select(GuestbookEntry))
    existing = list(result.scalars().all())
    if existing:
        return 0

    base_time = utc_now - timedelta(hours=48)

    def _gbmake(**kw):
        data = dict(
            status="approved",
            is_pinned=False,
            is_featured=False,
            likes_count=0,
            deleted_at=None,
            created_at=base_time,
            updated_at=base_time,
            avatar_source="auto",
        )
        data.update(kw)
        return GuestbookEntry(**data)

    entries = [
        _gbmake(
            user_id=admin_id,
            author_name="Choyeon",
            author_email="choyeon@foxmail.com",
            author_website="https://rosetta.choyeon.cc",
            author_ip="127.0.0.1",
            author_user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
            qq=None,
            github="Choyeon",
            avatar_source="github",
            content="欢迎来到 Rosetta 留言板！🎉 这里是博客的「开放式聊天室」，不管是建议、疑问、踩坑分享、还是就想打个招呼，都尽管留下你的足迹。每一条我都会认真阅读并回复。建站初衷：记录成长，分享知识，连接同路人～",
            is_pinned=True,
            likes_count=12,
            created_at=base_time,
            updated_at=base_time,
        ),
    ]

    # 5 条游客真实人物留言
    sampled = rng.sample(personas, k=min(5, len(personas)))
    guestbook_texts = [
        "博客主题质感真棒！配色看着很舒服，请问是用什么技术栈做的？已收藏 RSS，以后常来～",
        "第一次留言！一直默默看你的技术文章，FastAPI 那篇帮我解决了项目里的一个大问题，特意过来感谢一下 🙏",
        "你好呀，我也是做全栈开发的，主栈 Vue + FastAPI，跟你博客内容方向高度一致，能不能交换个友情链接？",
        "之前看你 GitHub 上的 Rosetta 仓库就觉得很惊艳，今天终于看到博客正式上线啦！祝福越做越好，期待更多深度文章。",
        "请问 RSS 订阅地址在哪里？找了半天没找到入口，建议侧边栏放个显眼的图标哈～顺便提一句，你的文章写得真的很清楚，小白也能看懂！",
    ]
    for i, (ps, text) in enumerate(zip(sampled, guestbook_texts)):
        entries.append(_gbmake(
            author_name=str(ps["nickname"]),
            author_email=(ps.get("email") or None),
            author_website=(ps.get("website") or None),
            author_ip=str(ps.get("ip_range") or "10.0.0.x"),
            author_user_agent=(ps.get("user_agent") or None),
            qq=(ps.get("qq") or None),
            github=(ps.get("github") or None),
            avatar_source=str(ps.get("avatar_source") or "auto"),
            content=text,
            is_featured=(i == 1),  # 第二条（感谢 FastAPI 那篇）做精华
            likes_count=rng.randint(1, 12),
            created_at=base_time + timedelta(hours=4 + i * 3, minutes=rng.randint(0, 59)),
            updated_at=base_time + timedelta(hours=4 + i * 3),
        ))

    # 1 条待审核（友链招募灰词）
    entries.append(_gbmake(
        author_name="神秘访客",
        author_email="visitor@example.com",
        author_website="https://unknown-site.example.com",
        author_ip="10.0.99.x",
        author_user_agent="Mozilla/5.0 (compatible; Mystery/1.0)",
        qq=None,
        github=None,
        avatar_source="auto",
        status="pending",
        content="你好，想和博主合作广告投放，我的资源质量很好，长期合作可以给你专属返佣，感兴趣联系我邮箱详聊！（本条为待审核示例）",
        created_at=base_time + timedelta(hours=30),
        updated_at=base_time + timedelta(hours=30),
    ))

    # 1 条管理员回复「交换友链」那条（index 3 的游客）
    entries.append(_gbmake(
        user_id=admin_id,
        author_name="Choyeon",
        author_email="choyeon@foxmail.com",
        author_website="https://rosetta.choyeon.cc",
        author_ip="127.0.0.1",
        author_user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
        qq=None,
        github="Choyeon",
        avatar_source="github",
        content="回复 3F 的朋友：友链当然可以呀！🙌 请通过 Email 或 QQ 联系我，附上你的站点名称、简介、头像链接即可，我收到后会第一时间安排上链。",
        likes_count=3,
        created_at=base_time + timedelta(hours=17),
        updated_at=base_time + timedelta(hours=17),
    ))

    for e in entries:
        db.add(e)
    await db.flush()
    return len(entries)


async def _oobe_create_sample_comments(db, post_id: int, admin_id: int) -> int:
    """保留兼容：旧版 Hello World 示例评论函数（新版流程不主动调用）。"""
    from backend.models.blog import Comment

    result = await db.execute(select(Comment).where(Comment.post_id == int(post_id)))
    existing = list(result.scalars().all())
    if existing:
        return 0

    base_time = datetime.now(UTC) - timedelta(hours=24)

    def _make(**kw):
        data = dict(
            post_id=int(post_id), status="approved", active=True, likes_count=0,
            is_pinned=False, created_at=base_time, updated_at=base_time,
        )
        data.update(kw)
        return Comment(**data)

    comments = [
        _make(author_name="王小二", author_email="wanger@example.com",
              author_website="https://wanger.example.com", author_ip="10.0.1.x",
              author_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
              content="写得非常好！受教了，谢谢博主分享，期待更多文章。"),
    ]
    for c in comments:
        db.add(c)
    await db.flush()
    return len(comments)


async def create_sample_guestbook_entries(db, admin_id: int) -> int:
    """保留兼容：旧版 5 条留言板（enhanced 版本才是新流程首选）。"""
    from backend.models.guestbook import GuestbookEntry

    result = await db.execute(select(GuestbookEntry))
    existing = list(result.scalars().all())
    if existing:
        return 0

    base_time = datetime.now(UTC) - timedelta(hours=48)

    def _gbmake(**kw):
        data = dict(
            status="approved", is_pinned=False, is_featured=False, likes_count=0,
            deleted_at=None, created_at=base_time, updated_at=base_time, avatar_source="auto",
        )
        data.update(kw)
        return GuestbookEntry(**data)

    entries = [
        _gbmake(user_id=admin_id, author_name="Choyeon", author_email="choyeon@foxmail.com",
                author_website="https://rosetta.choyeon.cc", author_ip="127.0.0.1",
                author_user_agent="Mozilla/5.0 (Macintosh)", avatar_source="github",
                github="Choyeon",
                content="欢迎来到 Rosetta 留言板！欢迎留下你的脚印、建议或问题。",
                is_pinned=True, likes_count=3),
    ]
    for e in entries:
        db.add(e)
    await db.flush()
    return len(entries)


async def main() -> None:
    """主函数"""
    from backend.core.database import init_db

    await init_db()
    await create_mock_data(num_posts=20, num_users=10, num_comments=50)


if __name__ == "__main__":
    asyncio.run(main())
