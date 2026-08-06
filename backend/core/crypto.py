"""
内容加密工具

基于 AES-GCM 对称加密算法，对文章敏感内容进行加解密。

设计：
- 使用 PBKDF2HMAC（SHA-256）从用户密码 + 随机 salt 派生 256 位密钥
- 每次加密生成随机 salt（16 字节）和 nonce（12 字节）
- 密文格式：base64(salt + nonce + ciphertext + gcm_tag)
- AES-GCM 的认证标签（tag）会自动附加在密文末尾，解密时一并校验

Example:
    >>> ct = encrypt_content("秘密内容", "my-password")
    >>> decrypt_content(ct, "my-password")
    '秘密内容'
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 参数常量
_SALT_LEN = 16
_NONCE_LEN = 12
_KEY_LEN = 32  # AES-256
_ITERATIONS = 100_000


class DecryptionError(Exception):
    """解密失败（密码错误或数据损坏）"""


def _derive_key(password: str, salt: bytes) -> bytes:
    """使用 PBKDF2HMAC 从密码和 salt 派生密钥"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_content(plaintext: str, password: str) -> str:
    """
    加密内容

    Args:
        plaintext: 待加密的明文
        password: 加密密码

    Returns:
        str: base64 编码的密文（包含 salt + nonce + ciphertext + tag）
    """
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = salt + nonce + ciphertext
    return base64.b64encode(blob).decode("ascii")


def decrypt_content(ciphertext_b64: str, password: str) -> str:
    """
    解密内容

    Args:
        ciphertext_b64: encrypt_content 返回的 base64 密文
        password: 解密密码

    Returns:
        str: 解密后的明文

    Raises:
        DecryptionError: 密码错误或密文损坏
    """
    try:
        blob = base64.b64decode(ciphertext_b64.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise DecryptionError("密文格式无效") from exc

    if len(blob) < _SALT_LEN + _NONCE_LEN:
        raise DecryptionError("密文长度不足")

    salt = blob[:_SALT_LEN]
    nonce = blob[_SALT_LEN : _SALT_LEN + _NONCE_LEN]
    ciphertext = blob[_SALT_LEN + _NONCE_LEN :]

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise DecryptionError("密码错误或密文已损坏") from exc

    return plaintext.decode("utf-8")
