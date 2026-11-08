"""
Rosetta 测试包
"""

import os

# pytest 导入 tests.conftest 之前必先执行本文件；而 conftest 在模块级 import
# backend.main，Settings() 也在模块级构造。若开发者本机 .env 写了
# APP_ENV=production，别名修复后测试会进入生产分支（强密钥校验 / 限流阈值 /
# docs 策略），用例集随机器漂移。环境变量优先级高于 .env 文件，且 ENVIRONMENT
# 在 AliasChoices 中排在 APP_ENV 之前，因此这里固定为 development。
os.environ.setdefault("ENVIRONMENT", "development")
