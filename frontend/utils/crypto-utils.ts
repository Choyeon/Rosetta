import AES from "crypto-js/aes";
import Utf8 from "crypto-js/enc-utf8";
import Base64 from "crypto-js/enc-base64";
import Hex from "crypto-js/enc-hex";
import SHA256 from "crypto-js/sha256";
import ECB from "crypto-js/mode-ecb";
import Pkcs7 from "crypto-js/pad-pkcs7";

/**
 * AES-256 加密（ECB + PKCS7；跨语言通用，短配置存储适用）。
 * @param plaintext 明文
 * @param key 任意字符串，内部 SHA-256 后截取 32 字节作密钥
 */
export function aesEncrypt(plaintext: string, key: string): string {
  if (!plaintext) return "";
  const secret = SHA256(key).toString(Hex).slice(0, 32);
  const encrypted = AES.encrypt(Utf8.parse(plaintext), Utf8.parse(secret), {
    mode: ECB,
    padding: Pkcs7,
  });
  return encrypted.toString();
}

/**
 * AES-256 解密；失败返回空字符串并 console.warn，不抛错。
 */
export function aesDecrypt(ciphertext: string, key: string): string {
  if (!ciphertext) return "";
  try {
    const secret = SHA256(key).toString(Hex).slice(0, 32);
    const decrypted = AES.decrypt(ciphertext, Utf8.parse(secret), {
      mode: ECB,
      padding: Pkcs7,
    });
    return decrypted.toString(Utf8);
  } catch (err) {
    console.warn("[crypto/aesDecrypt] 解密失败", err);
    return "";
  }
}

/**
 * URL-Safe Base64：替换 +/= 为 URL 安全字符，便于 query / path 透传。
 */
export function base64UrlEncode(input: string): string {
  const words = Utf8.parse(input);
  const b64 = Base64.stringify(words);
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function base64UrlDecode(input: string): string {
  let b64 = input.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4;
  if (pad) b64 += "=".repeat(4 - pad);
  try {
    const words = Base64.parse(b64);
    return Utf8.stringify(words);
  } catch {
    return "";
  }
}

/**
 * SHA-256 摘要，返回 hex 字符串。
 */
export function sha256(input: string): string {
  if (!input) return "";
  return SHA256(input).toString(Hex);
}

/**
 * 生成一个适合放 cookie / localStorage 的签名（hmac-like），
 * 用于弱场景「防篡改」，高强度鉴权请走服务端。
 */
export function weakSign(payload: Record<string, unknown> | string, salt: string): string {
  const body = typeof payload === "string" ? payload : JSON.stringify(payload);
  return sha256(`${salt}::${body}`).slice(0, 16);
}
