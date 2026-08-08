"""临时脚本：合并并生成 backend/scripts/oobe_seed_data.py
包含：OOBE_CATEGORIES, OOBE_TAGS, ARTICLE_TEMPLATES_V3 (32篇),
      COMMENT_PERSONAS (30人), COMMENT_CONTENT_TEMPLATES, ACTIVITY_TEMPLATES
"""
import ast
import pathlib
import re

WORK = pathlib.Path(r"D:\WebProjects\Rosetta")
SEED_A = pathlib.Path(r"c:\Users\Choyeon\seed_data.py")
SEED_B = WORK / "ARTICLE_TEMPLATES_V2.py"
OUT = WORK / "backend" / "scripts" / "oobe_seed_data.py"


def exec_src(src: str):
    g = {}
    exec(compile(src, "<seed>", "exec"), g)
    return g


# --- 1. 解析 OOBE_CATEGORIES / OOBE_TAGS / ARTICLE_TEMPLATES_V2 (前5篇) ---
def extract_var(source_lines, var_name):
    start = None
    for i, line in enumerate(source_lines):
        if re.match(rf"^{re.escape(var_name)}\s*=\s*", line):
            start = i
            break
    if start is None:
        raise ValueError(f"Var {var_name} not found")
    end = len(source_lines)
    for j in range(start + 1, len(source_lines)):
        if re.match(r"^[A-Z][A-Z0-9_]{1,40}\s*=\s*", source_lines[j]):
            end = j
            break
    block = "\n".join(source_lines[start:end])
    g = exec_src(block)
    return g[var_name]


lines_a = SEED_A.read_text(encoding="utf-8").splitlines()
OOBE_CATEGORIES = extract_var(lines_a, "OOBE_CATEGORIES")
OOBE_TAGS = extract_var(lines_a, "OOBE_TAGS")
ARTICLES_FIRST5 = extract_var(lines_a, "ARTICLE_TEMPLATES_V2")
print(f"Categories={len(OOBE_CATEGORIES)} Tags={len(OOBE_TAGS)} ArticlesFirst5={len(ARTICLES_FIRST5)}")

# --- 2. 解析 ARTICLE_TEMPLATES_V2.py (后27篇，只是逗号分隔的 dicts) ---
art_b_src = SEED_B.read_text(encoding="utf-8")
# 外层包成一个 list 赋值语句
art_b_wrapped = "ARTICLES_LAST27 = [\n" + art_b_src + "\n]\n"
g_b = exec_src(art_b_wrapped)
ARTICLES_LAST27 = g_b["ARTICLES_LAST27"]
print(f"Articles Last27 = {len(ARTICLES_LAST27)}")

ARTICLE_TEMPLATES_V3 = ARTICLES_FIRST5 + ARTICLES_LAST27
assert len(ARTICLE_TEMPLATES_V3) == 32, f"Expected 32, got {len(ARTICLE_TEMPLATES_V3)}"
print(f"Total articles = {len(ARTICLE_TEMPLATES_V3)}")

# --- 3. 内联写入 COMMENT_PERSONAS / COMMENT_CONTENT_TEMPLATES / ACTIVITY_TEMPLATES ---
# (内容由子代理生成，这里直接硬编码写进输出模块)

COMMENT_PERSONAS = [
    {"nickname": "代码幽灵", "email": "ghost.code@example.com", "website": "https://ghostdev.blog", "qq": "123456789", "github": "ghost-coder", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36", "ip_range": "10.0.1.x", "style": "detailed"},
    {"nickname": "奶茶味程序媛", "email": "milktea.dev@example.com", "website": None, "qq": "987654321", "github": None, "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15", "ip_range": "10.0.2.x", "style": "short"},
    {"nickname": "熬夜攻城狮", "email": "nightowl.eng@example.com", "website": "https://nightowl.tech", "qq": None, "github": "nightowl-engineer", "avatar_source": "github", "user_agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0", "ip_range": "10.0.3.x", "style": "question"},
    {"nickname": "像素小贩", "email": "pixel.seller@example.com", "website": "https://pixelart.studio", "qq": "55667788", "github": "pixel-designer", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0", "ip_range": "10.0.4.x", "style": "praise"},
    {"nickname": "摸鱼达人小王", "email": "moyu.wang@example.com", "website": None, "qq": "112233445", "github": None, "avatar_source": "qq", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1", "ip_range": "10.0.5.x", "style": "suggest"},
    {"nickname": "产品汪本汪", "email": "pm.dog@example.com", "website": "https://pmdiary.io", "qq": None, "github": "pm-dog", "avatar_source": "github", "user_agent": "Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1", "ip_range": "10.0.6.x", "style": "detailed"},
    {"nickname": "独立开发者阿明", "email": "aming.solo@example.com", "website": "https://aming.dev", "qq": "334455667", "github": "aming-solo", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36", "ip_range": "10.0.7.x", "style": "short"},
    {"nickname": "东京留学僧", "email": "tokyo.study@example.com", "website": None, "qq": None, "github": "tokyo-student", "avatar_source": "github", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "ip_range": "10.0.8.x", "style": "question"},
    {"nickname": "运维老司机", "email": "ops.driver@example.com", "website": "https://ops-notes.cn", "qq": "998877665", "github": "ops-old-driver", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36", "ip_range": "10.0.9.x", "style": "praise"},
    {"nickname": "架构师小李", "email": "arch.li@example.com", "website": "https://archinsights.blog", "qq": None, "github": "archer-li", "avatar_source": "github", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0", "ip_range": "10.0.10.x", "style": "suggest"},
    {"nickname": "DBA界的卷王", "email": "dba.king@example.com", "website": None, "qq": "135792468", "github": "dba-king", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15", "ip_range": "10.0.11.x", "style": "detailed"},
    {"nickname": "安全小白白", "email": "sec.newbie@example.com", "website": "https://seclab.digital", "qq": None, "github": "sec-newbie", "avatar_source": "github", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/127.0.0.0 Mobile/15E148 Safari/604.1", "ip_range": "10.0.12.x", "style": "short"},
    {"nickname": "画画的小鱼", "email": "draw.fish@example.com", "website": "https://fishgallery.art", "qq": "246801357", "github": None, "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15", "ip_range": "10.0.13.x", "style": "question"},
    {"nickname": "游戏策划阿哲", "email": "game.zhe@example.com", "website": None, "qq": None, "github": "game-zhe", "avatar_source": "github", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0", "ip_range": "10.0.14.x", "style": "praise"},
    {"nickname": "考研加油鸭", "email": "kaoyan.duck@example.com", "website": "https://kaoyan-journey.xyz", "qq": "778899001", "github": None, "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36", "ip_range": "10.0.15.x", "style": "suggest"},
    {"nickname": "前端艺术家", "email": "fe.artist@example.com", "website": "https://fe-gallery.dev", "qq": None, "github": "fe-artist", "avatar_source": "github", "user_agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "ip_range": "10.0.16.x", "style": "detailed"},
    {"nickname": "算法小菜鸟", "email": "algo.noob@example.com", "website": None, "qq": "667788990", "github": "algo-noob", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36", "ip_range": "10.0.17.x", "style": "short"},
    {"nickname": "云端漫步", "email": "cloud.walker@example.com", "website": "https://cloud-notes.cloud", "qq": None, "github": "cloud-walker", "avatar_source": "github", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/129.0 Mobile/15E148 Safari/605.1.15", "ip_range": "10.0.18.x", "style": "question"},
    {"nickname": "后端螺丝钉", "email": "be.screw@example.com", "website": "https://backend-diary.com", "qq": "100200300", "github": None, "avatar_source": "qq", "user_agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0", "ip_range": "10.0.19.x", "style": "praise"},
    {"nickname": "全栈打工人", "email": "fs.worker@example.com", "website": None, "qq": None, "github": "fullstack-worker", "avatar_source": "github", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36", "ip_range": "10.0.20.x", "style": "suggest"},
    {"nickname": "数据库小管家", "email": "db.butler@example.com", "website": "https://dbtips.pro", "qq": "500600700", "github": "db-butler", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Android 14; Tablet) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36", "ip_range": "10.0.21.x", "style": "detailed"},
    {"nickname": "自由撰稿人阿秋", "email": "qiu.writer@example.com", "website": "https://qiuwrites.blog", "qq": None, "github": None, "avatar_source": "auto", "user_agent": "Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/128.0.0.0 Version/18.0 Mobile/15E148 Safari/605.1.15", "ip_range": "10.0.22.x", "style": "short"},
    {"nickname": "AI炼丹学徒", "email": "ai.alchemist@example.com", "website": None, "qq": "800900100", "github": "ai-alchemist", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36", "ip_range": "10.0.23.x", "style": "question"},
    {"nickname": "DevOps小能手", "email": "devops.hero@example.com", "website": "https://devops-lab.cn", "qq": None, "github": "devops-hero", "avatar_source": "github", "user_agent": "Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "ip_range": "10.0.24.x", "style": "praise"},
    {"nickname": "测试小瓢虫", "email": "qa.bug@example.com", "website": None, "qq": "303404505", "github": None, "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15", "ip_range": "10.0.25.x", "style": "suggest"},
    {"nickname": "嵌入式极客", "email": "embedded.geek@example.com", "website": "https://embedded-lab.io", "qq": None, "github": "embedded-geek", "avatar_source": "github", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1", "ip_range": "10.0.26.x", "style": "detailed"},
    {"nickname": "机器学习萌新", "email": "ml.fresh@example.com", "website": None, "qq": "606707808", "github": "ml-fresh", "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36", "ip_range": "10.0.27.x", "style": "short"},
    {"nickname": "开源贡献者小Z", "email": "opensource.z@example.com", "website": "https://oss-z.dev", "qq": None, "github": "opensource-z", "avatar_source": "github", "user_agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0", "ip_range": "10.0.28.x", "style": "question"},
    {"nickname": "咖啡与代码", "email": "coffee.code@example.com", "website": None, "qq": "101010101", "github": None, "avatar_source": "qq", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0", "ip_range": "10.0.29.x", "style": "praise"},
    {"nickname": "技术笔记控", "email": "tech.notes@example.com", "website": "https://tech-notes.fun", "qq": None, "github": "tech-notes", "avatar_source": "github", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36", "ip_range": "10.0.30.x", "style": "suggest"},
]

COMMENT_CONTENT_TEMPLATES = {
    "backend": [
        "受益匪浅，感谢大佬分享！",
        "请问一下，文中提到的连接池配置，如果是在高并发场景下，一般设置多少比较合适？",
        "补充一点：实际使用中如果遇到 MySQL 的 8 小时超时问题，可以在连接串里加 autoReconnect=true 参数，虽然官方不推荐但挺好用的。",
        "楼主，我按照你的步骤操作后启动报错：Error creating bean with name 'dataSource'，版本是 Spring Boot 3.2，请问有遇到过吗？",
        "写得太好了，终于搞懂了分布式事务的几种方案区别，收藏了！",
        "建议加一下关于幂等性的讨论，现在的分布式系统里这个真的太重要了，很多坑都是没处理好幂等导致的。",
        "太及时了，正好项目里要上 Redis 集群，照着来一遍省了好多事，谢谢！",
        "有个小问题：你文中用的是 @Async 注解，这个默认用的是 SimpleAsyncTaskExecutor，生产环境是不是最好手动配一个线程池？",
        "好文！但是我觉得第三部分那个消息队列选型对比表有点偏向 Kafka 了，RocketMQ 在事务消息这块其实优势挺明显的。",
        "哈哈，楼主的踩坑经历和我一模一样！我当时就是没注意到这个配置，排查了整整两天，看到这篇文章泪目了。",
        "代码示例里那个 SQL 查询是不是应该加个 LIMIT？不然数据量大的时候全表扫描会很慢哦。",
        "作为一个刚入行的后端新人，这篇文章帮我理清了好多概念，谢谢博主持续输出高质量内容！",
    ],
    "frontend": [
        "感谢分享，刚好需要这个！",
        "博主请问一下，Next.js 15 里这个写法在 App Router 下会有 hydration 不匹配的问题吗？我用的时候偶尔报错。",
        "补充：用 CSS container query 实现响应式其实比媒体查询更灵活，组件级别的适配体验会好很多。",
        "按你的代码跑了一下，为什么在 Safari 下过渡动画会卡帧？Chrome 和 Firefox 都正常。",
        "终于有人把 CSS Grid 的各种布局技巧讲明白了，我之前看 MDN 文档看半天没搞懂，看完这篇直接上手了！",
        "建议可以加一下关于无障碍访问（a11y）的部分，现在很多项目都不重视这块，但真的很重要。",
        "这个组件封装得太优雅了，拿走直接用在项目里了，省了我半天时间，给博主点个大大的赞！",
        "请问一下，React 18 里用 useTransition 配合 Suspense 和直接用 lazy loading 有什么本质区别吗？什么时候该用哪个？",
        "示例代码里那个 useEffect 的依赖数组好像少了个参数，严格模式下会触发两次，建议修正一下。",
        "看到博主推荐的这个 UI 组件库了，之前一直在纠结选哪个，试了一下确实不错，文档也很友好！",
        "作为一个后端转全栈的，看你的前端文章从来不会觉得难懂，讲得特别接地气，谢谢！",
        "有个小小的建议：代码示例如果能加上语法高亮和行号就更好啦，阅读体验会更上一层楼～",
    ],
    "devops": [
        "干货满满，收藏吃灰！",
        "请教一下博主：Kubernetes 里 StatefulSet 和 Deployment 除了有序启动外，在存储这块具体有什么区别？什么时候必须用 StatefulSet？",
        "补充一个小技巧：用 kubectl 的 kubectx + kubens 插件切换集群和命名空间超级方便，谁用谁知道。",
        "按照你的教程搭建完 Prometheus + Grafana 监控后，节点 exporter 的数据采集延迟挺高的，这个正常吗？",
        "太好了！终于有人把 CI/CD 的完整流程讲清楚了，之前看了好多文章都是只讲一半，跟着这篇一步步跑通了整个流水线。",
        "建议可以再加一下关于成本优化的部分，云上资源如果不注意优化的话，账单真的会吓死个人。",
        "博主太懂运维的痛了！那个日志系统选型的部分我太有共鸣了，之前选型踩的坑和你说的一模一样。",
        "想请教一下：生产环境的 etcd 集群一般推荐几个节点？3 个和 5 个在性能和可用性上该怎么权衡？",
        "看到你那个 Nginx 配置示例，有个安全问题：server_tokens 建议关掉，不然会暴露 Nginx 版本号给攻击者。",
        "哈哈，备份不验证等于没备份那段我笑了，我之前就是吃了这个大亏，数据库备份了半年才发现根本恢复不了。",
        "非常棒的文章，就是希望能再深入讲讲容器镜像优化这块，我现在的镜像打包出来都 1G 多，感觉太臃肿了。",
        "终于找到一篇不吹不黑的 K8s 入门指南了，之前看的文章要么太浅要么上来就一堆概念，你这个循序渐进的节奏我太喜欢了！",
    ],
    "database": [
        "大佬讲得太通透了，收藏！",
        "请问一下：MySQL 里一张表数据量超过多少万行的时候才需要考虑分库分表？有没有什么比较通用的判断标准？",
        "补充一点：PostgreSQL 的 CTE（WITH 子句）在 12 版本之前是优化栅栏，如果涉及大数据量一定要注意，可能会导致严重的性能问题。",
        "照着你给的索引优化方案执行后，查询速度从 3 秒降到了 50 毫秒！太感谢了，困扰我一周的问题终于解决了。",
        "终于搞懂了 B+ 树索引和哈希索引的适用场景，之前面试被问到一直回答不好，现在终于可以说清楚了！",
        "建议后面可以专门写一篇关于 SQL 调优的实战文章，最好拿真实的慢查询案例来一步步拆解优化过程，那样会更有参考价值。",
        "关于你提到的那个慢查询分析工具 pt-query-digest，我补充一下：配合 Anemometer 做可视化展示效果会更好，谁用谁知道。",
        "博主，我有一个疑问：为什么有时候加了索引反而查询变慢了？我遇到过好几次这种情况，一直不知道原因。",
        "文章里那个事务隔离级别的表格写得很好，但有个小错误：MySQL 的 InnoDB 在可重复读隔离级别下其实是可以防止幻读的，用了 next-key lock。",
        "太真实了！那个线上事故案例我之前也遇到过类似的，备份恢复的时候没验证，等到真出问题的时候才发现备份是坏的，差点失业。",
        "能不能再讲讲 Redis 的持久化？RDB 和 AOF 混用的时候数据恢复顺序到底是怎样的？看文档有点懵。",
        "作为一个刚转 DBA 的开发，你的数据库文章是我见过最容易理解的，讲原理不空洞，讲实战有依据，太感谢你坚持分享了！",
    ],
    "ai": [
        "太硬核了，感谢分享！",
        "想请教一下：微调大模型的时候，LoRA 和全量微调除了显存占用不同，在最终效果上差异大吗？一般小数据集推荐用哪种？",
        "补充：向量数据库选型的时候，如果是中小规模的数据（百万级以内），其实用 PostgreSQL 的 pgvector 插件就完全够用了，不用上专门的向量数据库。",
        "按照你的教程跑了一个 RAG demo，但是回答经常会出现幻觉，引用的文档内容和实际不匹配，这个一般该从哪几个方向优化？",
        "看了这篇文章终于搞懂了 Transformer 的 Attention 机制！之前看了好多论文和视频都云里雾里，你画的那个流程图太关键了。",
        "建议可以加一下关于 Prompt Engineering 的系统性总结，虽然现在大家都说 Prompt 工程师会被淘汰，但实际用的时候好的 Prompt 和差的效果差太远了。",
        "博主推荐的那个开源 Embedding 模型我试了一下，在中文语义相似度任务上效果确实比 OpenAI 的 text-embedding-3 还要好一点，关键是能本地部署，太棒了！",
        "请问一下：大模型推理的时候温度（temperature）参数和 top_p 参数在实际使用中该怎么搭配？有没有什么经验值？",
        "文章里那个 Agent 的流程图我觉得有个地方可以商榷：工具调用的结果是不是应该先做一次 Relevance Check 再送回 LLM？不然如果工具返回了无关内容会影响最终效果。",
        "哈哈，那个用大模型写代码然后 Debug 到怀疑人生的经历太有共鸣了！我现在是 AI 写 100 行，我要改 80 行，但总体还是比纯手写快那么一点点。",
        "能不能专门写一篇关于多模态大模型微调的文章？现在图文理解的需求越来越多，但这方面的中文资料真的太少了。",
        "作为一个从传统开发转 AI 应用的程序员，你的文章帮我少走了好多弯路，每篇都不水，都是真刀真枪的实战经验，必须支持一下！",
    ],
}

ACTIVITY_TEMPLATES = [
    {"type": "say", "zh": "今天终于搞懂了 Go 语言中 goroutine 和 channel 的协作模式，之前看了好多资料都云里雾里，写了个小 demo 突然就开窍了，果然动手才是最好的老师。", "en": "Finally grasped how Go goroutines and channels work together today. Read tons of docs without getting it, but writing a tiny demo made everything click. Practice really does make perfect.", "ja": "今日はやっとGoのgoroutineとchannelの連携パターンが理解できた。資料をたくさん読んでもピンと来なかったけど、小さなdemoを書いたら急に腑に落ちた。やっぱり手を動かすのが一番だ。", "zh_Hant": "今天終於搞懂了 Go 語言中 goroutine 和 channel 的協作模式，之前看了好多資料都雲裡霧裡，寫了個小 demo 突然就開竅了，果然動手才是最好的老師。"},
    {"type": "say", "zh": "窗外下起了今年第一场秋雨，泡了杯桂花乌龙，听着雨声改代码，突然觉得做程序员也挺幸福的，就是颈椎有点抗议。", "en": "The first autumn rain of the year is falling outside. Brewed some osmanthus oolong, fixing bugs while listening to the raindrops. Being a programmer feels kinda peaceful right now — except my neck is complaining.", "ja": "窓の外は今年初めての秋雨。桂花烏龍茶を淹れて、雨音を聞きながらコードを直している。プログラマーも悪くないなと思う瞬間、首が悲鳴を上げている。", "zh_Hant": "窗外下起了今年第一場秋雨，泡了杯桂花烏龍，聽著雨聲改程式碼，突然覺得做程式設計師也挺幸福的，就是頸椎有點抗議。"},
    {"type": "article", "zh": "📝 新文章预告：《从零搭建一个高可用的 Redis 集群》，下周更新，会详细讲哨兵模式、集群分片、故障演练，以及我踩过的7个坑，订阅不迷路～", "en": "📝 New article preview: Building a High-Availability Redis Cluster from Scratch. Coming next week — covers Sentinel, sharding, failover drills, and 7 pitfalls I stepped into. Subscribe so you don't miss it!", "ja": "📝 新記事予告：『ゼロから作る高可用Redisクラスタ』。来週公開予定。Sentinelモード、クラスタシャーディング、フェイルオーバー検証、そして私が踏んだ7つの罠を詳しく解説する。お楽しみに〜", "zh_Hant": "📝 新文章預告：《從零搭建一個高可用的 Redis 叢集》，下週更新，會詳細講哨兵模式、叢集分片、故障演練，以及我踩過的7個坑，訂閱不迷路～"},
    {"type": "say", "zh": "强烈推荐一个命令行工具 `fzf`，模糊查找太香了！配合 `zoxide` 用，cd 命令直接失业，现在我手速快得连自己都害怕。", "en": "Can't recommend `fzf` enough — fuzzy searching in the terminal is *chef's kiss*. Pair it with `zoxide` and your `cd` command becomes obsolete. I'm navigating so fast now it scares me.", "ja": "コマンドラインツールの`fzf`を激推ししたい。曖昧検索が最高に便利！`zoxide`と併用したら`cd`コマンドが要らなくなった。自分でも怖いくらい操作が速くなった。", "zh_Hant": "強烈推薦一個命令列工具 `fzf`，模糊查詢太香了！配合 `zoxide` 用，cd 命令直接失業，現在我手速快得連自己都害怕。"},
    {"type": "update", "zh": "🔧 博客小更新：夜间模式现在支持跟随系统啦！另外修复了图片懒加载在 Safari 下偶尔不触发的 bug，感谢反馈的朋友们 ❤️", "en": "🔧 Blog update: Dark mode now follows system preferences! Also fixed a bug where lazy loading images sometimes wouldn't trigger in Safari. Thanks everyone who reported it ❤️", "ja": "🔧 ブログのアップデート：ダークモードがシステム設定に追従するようになった！あとSafariでたまに画像の遅延読み込みが発動しないバグを修正。報告してくれた皆、ありがとう❤️", "zh_Hant": "🔧 部落格小更新：夜間模式現在支援跟隨系統啦！另外修復了圖片懶載入在 Safari 下偶爾不觸發的 bug，感謝回饋的朋友們 ❤️"},
    {"type": "say", "zh": "周末去跑了个5公里，虽然配速慢得像散步，但跑完吃了碗热腾腾的牛肉面，值了！身体是革命的本钱，各位程序员也要多动动。", "en": "Went for a 5K run this weekend. Pace was basically a brisk walk, but rewarded myself with a steaming bowl of beef noodles afterward — worth it! Health is wealth, fellow devs, go move your bodies.", "ja": "週末に5km走った。ペースはただの散歩並みだったけど、走り終わって熱々の牛肉麺を食べたら全部報われた。体が資本だ。プログラマーの皆さんもたまには動こう。", "zh_Hant": "週末去跑了個5公里，雖然配速慢得像散步，但跑完吃了碗熱騰騰的牛肉麵，值了！身體是革命的本錢，各位程式設計師也要多動動。"},
    {"type": "say", "zh": "最近在学 Rust，所有权系统真的让我又爱又恨。编译报错的时候真想把电脑砸了，但编译通过的那一刻，啊~多巴胺爆炸。", "en": "Learning Rust lately and the ownership system is a love-hate relationship. When the compiler yells at me I want to throw my laptop out the window, but when it passes? Pure dopamine rush.", "ja": "最近Rustを勉強中。所有権システムは本当に好き嫌いが激しい。コンパイラに怒られるとパソコンを投げ出したくなるけど、通った瞬間はドーパミン大爆発だ。", "zh_Hant": "最近在學 Rust，所有權系統真的讓我又愛又恨。編譯報錯的時候真想把電腦砸了，但編譯通過的那一刻，啊~多巴胺爆炸。"},
    {"type": "notice", "zh": "📢 维护通知：本周六凌晨2点-4点将进行服务器迁移，期间博客可能短暂无法访问，给大家带来的不便敬请谅解，迁移完成后速度会有明显提升！", "en": "📢 Maintenance notice: Server migration this Saturday 2–4 AM. Blog may be briefly unavailable during that time. Sorry for the inconvenience — you'll get a nice speed boost afterward!", "ja": "📢 メンテナンスのお知らせ：今週土曜日の午前2時〜4時にサーバー移行を行います。その間、ブログに一時的にアクセスできないことがあります。ご不便をおかけしてすみません。移行完了後は速度が大幅にアップします！", "zh_Hant": "📢 維護通知：本週六凌晨2點-4點將進行伺服器遷移，期間部落格可能短暫無法存取，帶給大家的不便敬請見諒，遷移完成後速度會有明顯提升！"},
    {"type": "say", "zh": "刚把用了三年的机械键盘换成了静电容，打字手感像踩在云朵上，就是钱包有点疼。不过嘛，写代码快乐度+50%，生产力提升这不就来了嘛。", "en": "Just swapped my 3-year-old mechanical keyboard for a Topre. Typing feels like stepping on clouds. My wallet hurts, but coding happiness is up 50% — productivity gains are basically guaranteed, right?", "ja": "3年使ったメカニカルキーボードを静電容量式に買い替えた。打鍵感が雲の上を歩いてるよう。財布は痛いけど、コーディングの幸せ度が50%アップ。生産性も上がるよね？たぶん。", "zh_Hant": "剛把用了三年的機械鍵盤換成了靜電容，打字手感像踩在雲朵上，就是錢包有點疼。不過嘛，寫程式快樂度+50%，生產力提升這不就來了嘛。"},
    {"type": "say", "zh": "分享一个调试小技巧：遇到奇怪的 bug 先别慌，去 git stash 清掉本地改动重新跑一遍，十次里有三次是我自己改了什么东西忘了。", "en": "Pro debugging tip: When you hit a weird bug, don't panic. Stash local changes and run it again fresh. 3 out of 10 times it's because I changed something and forgot.", "ja": "デバッグの小ネタ：謎のバグに遭ったらまず慌てない。git stashでローカルの変更を避けてからもう一度実行してみよう。10回に3回は自分が何か変更したのを忘れてるだけだ。", "zh_Hant": "分享一個除錯小技巧：遇到奇怪的 bug 先別慌，去 git stash 清掉本地改動重新跑一遍，十次裡有三次是我自己改了什麼東西忘了。"},
    {"type": "article", "zh": "📚 读了本好书《Designing Data-Intensive Applications》，真的是后端架构师的圣经，每一页都在刷新认知，准备写一篇读书笔记整理重点。", "en": "📚 Reading Designing Data-Intensive Applications — absolute bible for backend architects. Every page blows my mind. Planning to write a book review with all the key takeaways soon.", "ja": "📚 『Designing Data-Intensive Applications』を読んでいる。バックエンドアーキテクトのバイブルだ。ページをめくるたびに認識が更新される。そのうち要点をまとめた読書ノートを書く予定。", "zh_Hant": "📚 讀了本好書《Designing Data-Intensive Applications》，真的是後端架構師的聖經，每一頁都在刷新認知，準備寫一篇讀書筆記整理重點。"},
    {"type": "say", "zh": "入秋了，今天的风有桂花香，下班路上买了袋糖炒栗子，生活嘛，不就是这些小确幸支撑着我们熬过一个个deadline。", "en": "Autumn is here — the wind smells like osmanthus today. Grabbed a bag of sugar-roasted chestnuts on my way home. These small happy moments are what get us through every deadline, aren't they?", "ja": "秋だ。今日の風は金木犀の香りがする。帰り道に栗きんとん（甘栗）を一袋買った。こういう小さな幸せが、たくさんの締め切りを乗り越える原動力なんだよね。", "zh_Hant": "入秋了，今天的風有桂花香味，下班路上買了袋糖炒栗子，生活嘛，不就是這些小確幸支撐著我們熬過一個個deadline。"},
    {"type": "say", "zh": "今天用 Python 的 asyncio 写了个爬虫，从同步改到异步后速度直接翻了8倍，感觉打开了新世界的大门，就是调试协程有点费头发。", "en": "Rewrote a crawler from sync to async with Python asyncio today — got an 8x speed boost. Feels like opening a door to a whole new world. Debugging coroutines does cost me some hair though.", "ja": "今日はPython asyncioでクローラーを書いた。同期版から非同期に書き換えたら速度が8倍になった。新世界の扉が開いた気分。ただコルーチンのデバッグは少し髪が抜ける。", "zh_Hant": "今天用 Python 的 asyncio 寫了個爬蟲，從同步改到非同步後速度直接翻了8倍，感覺打開了新世界的大門，就是除錯協程有點費頭髮。"},
    {"type": "update", "zh": "✨ 新功能上线：博客评论区现在支持表情反应啦！可以给喜欢的评论点个❤️或者😂，另外还加了评论点赞功能，快去试试吧~", "en": "✨ New feature: Comment reactions are live! You can now react to comments with ❤️ 😂 and more. Also added comment upvotes. Go try them out!", "ja": "✨ 新機能リリース：コメント欄にリアクションボタンを追加！❤️や😂などで好きなコメントに反応できるよ。あとコメントのいいね機能も。早速使ってみて〜", "zh_Hant": "✨ 新功能上線：部落格評論區現在支援表情反應啦！可以給喜歡的評論點個❤️或者😂，另外還加了評論點贊功能，快去試試吧~"},
    {"type": "say", "zh": "今天面试了一个应届生，算法题写得一塌糊涂但简历上写了一堆开源项目贡献。让他讲了讲PR的内容，思路清晰得一批，当场就决定要了。", "en": "Interviewed a new grad today. Flubbed the algorithm questions but had tons of OSS contributions on their resume. Had them walk through their PRs — super clear thinking. Hired them on the spot.", "ja": "今日、新卒の学生を面接した。アルゴリズム問題はボロボロだったけど、履歴書にはOSSコントリビューションがぎっしり。PRの内容を説明してもらったら思考がすごく明確で、即採用に決めた。", "zh_Hant": "今天面試了一個應屆生，演算法題寫得一塌糊塗但履歷上寫了一堆開源專案貢獻。讓他講了講PR的內容，思路清晰得一批，當場就決定要了。"},
    {"type": "say", "zh": "推荐一个开源项目：`helix-editor`，终端下的模态编辑器，类似 Vim 但用 Rust 写的，内置 LSP 和树-sitter，配置是 TOML 不用学 Vimscript，真香。", "en": "Hot take: Check out `helix-editor` — a terminal modal editor like Vim but written in Rust. Built-in LSP + tree-sitter, config is TOML so no Vimscript to learn. *Chef's kiss.*", "ja": "おすすめOSS：`helix-editor`。ターミナルで動くモーダルエディタ。VimみたいだけどRust製。LSPとtree-sitterが標準搭載で、設定はTOMLなのでVimscriptを学ばなくてOK。最高。", "zh_Hant": "推薦一個開源專案：`helix-editor`，終端下的模態編輯器，類似 Vim 但用 Rust 寫的，內建 LSP 和樹-sitter，配置是 TOML 不用學 Vimscript，真香。"},
    {"type": "say", "zh": "深夜食堂开张：今天吃什么呢？番茄牛腩盖饭配半熟蛋，再配一瓶冰可乐。吃饱了才有力气接着写 bug，啊不，写代码。", "en": "Late-night dinner menu: Beef tomato rice bowl with a soft-boiled egg and a cold Coke. Gotta fuel up before writing more bugs — I mean, code.", "ja": "深夜食堂開店：今日のメニューはトマト牛肉丼に半熟卵、あと冷たいコーラ。お腹いっぱいにならないとバグを…じゃなかった、コードを書く元気が出ない。", "zh_Hant": "深夜食堂開張：今天吃什麼呢？番茄牛腩蓋飯配半熟蛋，再配一瓶冰可樂。吃飽了才有力氣接著寫 bug，啊不，寫程式碼。"},
    {"type": "article", "zh": "📝 新文章发布：《Docker 容器化部署实战指南》，从 Dockerfile 最佳实践到 docker-compose 编排再到生产环境注意事项，图文并茂附完整示例代码～", "en": "📝 New post: Practical Guide to Docker Container Deployment. Covers Dockerfile best practices, docker-compose orchestration, and production considerations. Full of diagrams and complete code examples ~", "ja": "📝 新記事公開：『Dockerコンテナ化デプロイ実践ガイド』。Dockerfileのベストプラクティスからdocker-composeのオーケストレーション、本番環境の注意点まで。図解多めで完全なサンプルコード付き〜", "zh_Hant": "📝 新文章發布：《Docker 容器化部署實戰指南》，從 Dockerfile 最佳實踐到 docker-compose 編排再到生產環境注意事項，圖文並茂附完整範例程式碼～"},
    {"type": "link", "zh": "🔗 读到一篇超棒的文章《为什么我们需要事件驱动架构》，把 EDA 的优缺点和适用场景讲得明明白白，建议所有后端同学都看看，链接放评论区。", "en": "🔗 Read a fantastic article: Why We Need Event-Driven Architecture. Breaks down EDA pros/cons and use cases so clearly. Every backend dev should read this. Link in comments.", "ja": "🔗 めちゃくちゃ良い記事を読んだ：『なぜイベント駆動アーキテクチャが必要なのか』。EDAの長所短所と適用シーンがすごく分かりやすく解説されてる。バックエンドの人は全員読むべき。リンクはコメント欄に。", "zh_Hant": "🔗 讀到一篇超棒的文章《為什麼我們需要事件驅動架構》，把 EDA 的優缺點和適用場景講得明明白白，建議所有後端同學都看看，連結放評論區。"},
    {"type": "say", "zh": "今天用了一天 Next.js 15 的 App Router，之前一直死守 Pages Router，现在只想说：真香。Server Components 配合 Suspense 加载体验太丝滑了。", "en": "Spent all day with Next.js 15 App Router after clinging to Pages Router forever. Verdict: It's amazing. Server Components + Suspense make the loading experience so smooth.", "ja": "今日一日中Next.js 15のApp Routerを使ってた。ずっとPages Routerから離れなかったけど、今となっては最高だと言いたい。Server ComponentsとSuspenseの組み合わせはローディング体験がすごくスムーズ。", "zh_Hant": "今天用了一天 Next.js 15 的 App Router，之前一直死守 Pages Router，現在只想說：真香。Server Components 配合 Suspense 載入體驗太絲滑了。"},
    {"type": "notice", "zh": "🤝 友链招募！如果你也有独立博客且内容质量不错，欢迎来交换友链～ 要求：建站3个月以上，原创文章≥20篇，无违规内容，评论区留链接我会去看哒！", "en": "🤝 Blogroll recruitment! If you have an indie blog with quality content, let's swap links! Requirements: 3+ months old, 20+ original posts, nothing sketchy. Drop your URL in comments and I'll check it out!", "ja": "🤝 相互リンク募集！インディーズブログを持っててコンテンツの質が良い方、ぜひリンク交換しましょう〜 条件：開設3ヶ月以上、オリジナル記事20本以上、違反内容なし。コメント欄にURLを置いてね！", "zh_Hant": "🤝 友鏈招募！如果你也有獨立部落格且內容品質不錯，歡迎來交換友鏈～ 要求：建站3個月以上，原創文章≥20篇，無違規內容，評論區留連結我會去看噠！"},
    {"type": "say", "zh": "分享一个编程心得：写代码前先写注释，把思路用中文写清楚，再填充实现，这样代码逻辑会清晰很多，还不容易写出 bug，强烈推荐试试。", "en": "Programming tip I swear by: Write comments first — describe your logic in plain language — then fill in the code. Way clearer thinking, way fewer bugs. Give it a try.", "ja": "プログラミングの心得：コードを書く前にまずコメントを書く。頭の中のロジックを自然言語で明確にしてから実装を埋めていくと、すごく整理されるしバグも減る。ぜひ試してみて。", "zh_Hant": "分享一個程式設計心得：寫程式碼前先寫註解，把思路用中文寫清楚，再填充實現，這樣程式碼邏輯會清晰很多，還不容易寫出 bug，強烈推薦試試。"},
    {"type": "say", "zh": "天气转凉了，大家记得加衣服，不要像我一样感冒了还要在被窝里改线上 bug，真的会谢。话说生姜可乐真的有用吗？", "en": "Weather's getting cold — bundle up, everyone. Don't end up like me: sick in bed but still fixing production bugs under the covers. This sucks. Also, does ginger Coke actually work?", "ja": "寒くなってきたので、皆さん風邪をひかないようにね。私みたいに布団の中で本番環境のバグを直すハメにならないように。あと、しょうがコーラって本当に効くの？", "zh_Hant": "天氣轉涼了，大家記得加衣服，不要像我一樣感冒了還要在被窩裡改線上 bug，真的會謝。話說生薑可樂真的有用嗎？"},
    {"type": "update", "zh": "🎨 博客 UI 大翻新！换了青蓝色调的主题，加了一些微交互动画，优化了移动端阅读体验。大家觉得新外观怎么样？欢迎提建议～", "en": "🎨 Blog UI overhaul! Switched to a blue-teal color palette, added subtle micro-interactions, optimized mobile reading. What do you all think of the new look? Suggestions welcome ~", "ja": "🎨 ブログのUIを大幅リニューアル！青と水色のトーンに変更して、細かいマイクロインタラクションを追加。モバイルの読み心地も改善。新しい見た目はどうかな？感想や提案があればぜひ〜", "zh_Hant": "🎨 部落格 UI 大翻新！換了青藍色調的主題，加了一些微互動動畫，優化了行動端閱讀體驗。大家覺得新外觀怎麼樣？歡迎提建議～"},
    {"type": "say", "zh": "刚入职的实习生问我：「前辈，怎么才能写出优雅的代码？」我想了想：「先写够十万行烂代码，再回头看你就懂了。」说完感觉自己像个武林高手。", "en": "My new intern asked: \"How do I write elegant code?\" I thought for a sec and said: \"First write 100,000 lines of garbage, then look back and you'll get it.\" Felt like a martial arts master after that.", "ja": "新しく来たインターンが「先輩、どうしたら綺麗なコードが書けますか？」って聞いてきた。ちょっと考えて「まず10万行くらい下手なコードを書きまくれ。それから見返せば分かる」って答えた。なんか武術の達人みたいな気分になった。", "zh_Hant": "剛入職的實習生問我：「前輩，怎麼才能寫出優雅的程式碼？」我想了想：「先寫夠十萬行爛程式碼，再回頭看你就懂了。」說完感覺自己像個武林高手。"},
]


# --- 4. 检查文章是否包含 {code} 占位，如未包含则自动插入代码块 ---
def ensure_article_format(a):
    a = dict(a)
    code = a.get("code_snippet") or ""
    def process(content):
        if not content:
            return content
        # 如果 {code} 已经存在则替换
        if "{code}" in content:
            return content.replace("{code}", f"```{a.get('code_language','')}\n{code.rstrip()}\n```")
        # 否则插入代码块到第一个 H2 之前（或第一段落之后）
        lines = content.splitlines(keepends=True)
        insert_at = 3
        for i, line in enumerate(lines):
            if line.startswith("## "):
                insert_at = i
                break
        code_block = f"\n```{a.get('code_language','')}\n{code.rstrip()}\n```\n\n"
        lines.insert(insert_at, code_block)
        return "".join(lines)

    if "content_zh" in a:
        a["content_zh"] = process(a.get("content_zh") or "")
    if "content_en" in a:
        a["content_en"] = process(a.get("content_en") or "")
    return a


ARTICLE_TEMPLATES_V3 = [ensure_article_format(a) for a in ARTICLE_TEMPLATES_V3]

# --- 5. 输出完整模块 ---
import pprint

def write_module():
    lines = []
    lines.append("# -*- coding: utf-8 -*-")
    lines.append('"""OOBE 一键部署真实种子数据（32篇四语言文章 + 真实评论 + 真实动态说说）"""')
    lines.append("")
    lines.append("__all__ = [")
    lines.append('    "OOBE_CATEGORIES",')
    lines.append('    "OOBE_TAGS",')
    lines.append('    "ARTICLE_TEMPLATES_V3",')
    lines.append('    "COMMENT_PERSONAS",')
    lines.append('    "COMMENT_CONTENT_TEMPLATES",')
    lines.append('    "ACTIVITY_TEMPLATES",')
    lines.append("]")
    lines.append("")
    lines.append(f"OOBE_CATEGORIES = {pprint.pformat(OOBE_CATEGORIES, sort_dicts=False, width=120)}")
    lines.append("")
    lines.append(f"OOBE_TAGS = {pprint.pformat(OOBE_TAGS, sort_dicts=False, width=120)}")
    lines.append("")
    # 文章太大，用 repr 自己拼（避免 pprint 内部换行破坏 markdown）
    lines.append("ARTICLE_TEMPLATES_V3 = [")
    for i, art in enumerate(ARTICLE_TEMPLATES_V3):
        lines.append("    " + pprint.pformat(art, sort_dicts=False, width=140) + ",")
    lines.append("]")
    lines.append("")
    lines.append(f"COMMENT_PERSONAS = {pprint.pformat(COMMENT_PERSONAS, sort_dicts=False, width=120)}")
    lines.append("")
    lines.append(f"COMMENT_CONTENT_TEMPLATES = {pprint.pformat(COMMENT_CONTENT_TEMPLATES, sort_dicts=False, width=120)}")
    lines.append("")
    lines.append(f"ACTIVITY_TEMPLATES = {pprint.pformat(ACTIVITY_TEMPLATES, sort_dicts=False, width=120)}")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


write_module()
print("SUCCESS")
