"""自助维护工具：把 public/ 下的密文解密出来编辑，改完加密回去并重建清单。

用法（在本仓库根目录执行）：
  python tools/update.py decode ui_texts    # 解密分类到 work/ 供编辑
  python tools/update.py decode all
  python tools/update.py encode ui_texts    # 把 work/ 的修改加密回 public/ 并重建 manifest
  python tools/update.py encode all
之后 git add -A && git commit && git push，Vercel 自动部署。

哈希算法与主仓库 manifest.py 完全一致；密钥默认 c13an，可用环境变量 DIST_KEY 覆盖。
"""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

KEY = os.environ.get("DIST_KEY") or "c13an"
TAG = "ENC:"
SEPARATOR = b"\x00"
PATH_SEPARATOR = "\x01"
ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
WORK = ROOT / "work"
PLAIN_CATEGORIES = ["names", "titles", "descriptions", "ui_texts", "static"]


def traverse(obj, prefix=""):
    for key, value in sorted(obj.items()):
        path = f"{prefix}{PATH_SEPARATOR}{key}" if prefix else key
        if isinstance(value, dict):
            yield from traverse(value, path)
        else:
            yield path, value


def obj_hash(obj) -> str:
    md5 = hashlib.md5()
    for key, value in traverse(obj):
        md5.update(key.encode("utf-8"))
        md5.update(SEPARATOR)
        md5.update(str(value).encode("utf-8"))
        md5.update(SEPARATOR)
    return md5.hexdigest()


def xor_bytes(data: bytes, key: bytes) -> bytes:
    if not data:
        return data
    pad = (len(key) - (len(data) % len(key))) % len(key)
    padded = data + b"\x00" * pad
    key_stream = (key * (len(padded) // len(key) + 1))[: len(padded)]
    return bytes(a ^ b for a, b in zip(padded, key_stream))[: len(data)]


def encode_raw(data: bytes) -> bytes:
    return (TAG + base64.b64encode(xor_bytes(data, KEY.encode())).decode()).encode()


def decode_file(path: Path, preserve_bytes=False) -> bytes:
    text = path.read_text(encoding="utf-8")
    if not text.startswith(TAG):
        raise ValueError(f"{path} 不是 {TAG} 密文")
    plain = xor_bytes(base64.b64decode(text[len(TAG):]), KEY.encode())
    if not preserve_bytes:
        json.loads(plain.decode("utf-8"))
    return plain


def encode_file(path: Path, data: bytes, compact=True):
    if compact:
        obj = json.loads(data.decode("utf-8"))
        data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode_raw(data))


def plain_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def category_paths(category: str) -> tuple[Path, Path]:
    return PUBLIC / category / "zh_Hans.json", WORK / f"{category}.zh_Hans.json"


def decode_one(category: str):
    src, dst = category_paths(category)
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(plain_json(json.loads(decode_file(src).decode("utf-8"))), encoding="utf-8")
    print(f"decoded {category} -> {dst.relative_to(ROOT)}")


def decode_replacements():
    out = WORK / "replacements"
    out.mkdir(exist_ok=True)
    src = PUBLIC / "replacements"
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        if f.suffix.lower() == ".json":
            (out / rel).write_bytes(decode_file(f, preserve_bytes=True))
            print(f"decoded replacements/{rel.as_posix()}")
        else:
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.read_bytes())
            print(f"copied  replacements/{rel.as_posix()}（图片无需解密）")


def encode_one(category: str):
    src, dst = category_paths(category)
    if not dst.exists():
        sys.exit(f"找不到 {dst}，请先 decode {category}")
    encode_file(src, dst.read_bytes())
    print(f"encoded {category} -> {src.relative_to(ROOT)}")


def encode_replacements():
    src = PUBLIC / "replacements"
    work = WORK / "replacements"
    if not work.exists():
        sys.exit("找不到 work/replacements，请先 decode all")
    for f in sorted(work.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(work)
        target = src / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if f.suffix.lower() == ".json":
            encode_file(target, f.read_bytes(), compact=False)
        else:
            target.write_bytes(f.read_bytes())
    print("encoded replacements")


def rebuild_manifest():
    manifest = {}
    for category in PLAIN_CATEGORIES:
        f = PUBLIC / category / "zh_Hans.json"
        if f.exists():
            manifest[category] = obj_hash(json.loads(decode_file(f).decode("utf-8")))

    rep_root = PUBLIC / "replacements"
    if rep_root.exists():
        manifest["replacements"] = {
            f.relative_to(rep_root).as_posix(): hashlib.md5(
                decode_file(f, preserve_bytes=True) if f.suffix.lower() == ".json" else f.read_bytes()
            ).hexdigest()
            for f in sorted(rep_root.rglob("*"))
            if f.is_file()
            and (
                (f.name == "manifest.json" and f.parent.name == "replacements")
                or f.suffix.lower() in {".png", ".jpg", ".jpeg"}
            )
        }

    novel_root = PUBLIC / "novels"
    if novel_root.exists():
        manifest["novels"] = {
            f.parent.name: obj_hash(json.loads(decode_file(f).decode("utf-8")))
            for f in sorted(novel_root.glob("*/zh_Hans.json"))
        }

    manifest["hash"] = obj_hash(manifest)
    out = PUBLIC / "manifest" / "zh_Hans.json"
    encode_file(
        out,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=4).encode("utf-8"),
    )
    print(f"manifest rebuilt -> {out.relative_to(ROOT)}")


def main():
    usage = __doc__
    if len(sys.argv) != 3 or sys.argv[1] not in ("decode", "encode"):
        print(usage)
        sys.exit(1)
    action, target = sys.argv[1], sys.argv[2]
    if action == "decode":
        if target == "all":
            for c in PLAIN_CATEGORIES:
                if (PUBLIC / c).exists():
                    decode_one(c)
            decode_replacements()
        elif target == "replacements":
            decode_replacements()
        else:
            decode_one(target)
    else:
        if target == "all":
            for c in PLAIN_CATEGORIES:
                if category_paths(c)[1].exists():
                    encode_one(c)
            if (WORK / "replacements").exists():
                encode_replacements()
        elif target == "replacements":
            encode_replacements()
        else:
            encode_one(target)
        rebuild_manifest()


if __name__ == "__main__":
    main()
