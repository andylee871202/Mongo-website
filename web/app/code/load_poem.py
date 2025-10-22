# -*- coding: utf-8 -*-
import os
import re
import csv
import sys
import json
import unicodedata as ud

from Mongo_manager import MongoManager

DATA_PATH = "/app/web/app/ori_data/poem.csv"
CTRL_RE = re.compile(r"[\x00-\x1F\x7F]")
SPACE_RE = re.compile(r"\s+")
CJK_RE = re.compile(r"[\u3400-\u9FFF\uF900-\uFAFF]")

def strip_ctrl(s: str | None) -> str:
    return CTRL_RE.sub("", s or "")

def normalize_text(s: str) -> str:
    """全半形統一 + 空白正規化（不做多餘欄位）"""
    s = strip_ctrl(s)
    s = ud.normalize("NFKC", s)
    s = SPACE_RE.sub(" ", s).strip()
    return s

def safe_int(x):
    try:
        return int(str(x).strip())
    except Exception:
        return None

def gen_search_text(title, form, era, author, content_norm):
    parts = [p for p in [title, form, era, author, content_norm] if p]
    return normalize_text(" ".join(parts))

def gen_ngrams_bi(s: str) -> list[str]:
    """中文字雙連詞（僅保留連續 CJK），去重保序"""
    compact = re.sub(r"\s+", "", s or "")
    grams = []
    for i in range(len(compact) - 1):
        a, b = compact[i], compact[i + 1]
        if CJK_RE.match(a) and CJK_RE.match(b):
            grams.append(a + b)
    seen, out = set(), []
    for g in grams:
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out

# ---------- 讀檔 + 寫入 ----------
def main():
    if not os.path.exists(DATA_PATH):
        sys.stderr.write(f"[error] data file not found: {DATA_PATH}\n")
        sys.exit(1)

    mgr = MongoManager()
    total, ok, fail = 0, 0, 0
    errors = []

    # 你的原始檔為「TSV」，所以 delimiter 設為 '\t'
    with open(DATA_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, r in enumerate(reader, start=1):
            total += 1
            try:
                ID = safe_int(r.get("編號"))
                if ID is None:
                    continue

                title = strip_ctrl(r.get("題名") or None)
                if title == "*":
                    title = None

                form = strip_ctrl(r.get("型式") or None)
                era = strip_ctrl(r.get("朝代") or None)
                author = strip_ctrl(r.get("作者") or None)
                content_raw = strip_ctrl(r.get("內容") or "")

                # 規格要求欄位
                content_norm = normalize_text(content_raw)
                search_text = gen_search_text(title, form, era, author, content_norm)
                ngrams_bi = gen_ngrams_bi(search_text)
                meta = {"chars": len(content_norm)}

                # 只送入你要求的 10 欄；created/updated 由 MongoManager 內部補
                mgr.insert_poem(
                    ID=ID,
                    title=title,
                    form=form,
                    era=era,
                    author=author,
                    content_raw=content_raw,
                    content_norm=content_norm,
                    search_text=search_text,
                    ngrams_bi=ngrams_bi,
                    meta=meta,
                )
                ok += 1

            except Exception as e:
                fail += 1
                # 收集錯誤，但不中斷整體流程
                errors.append({"line": i, "error": str(e)})

    mgr.close()

    result = {
        "status": "ok" if fail == 0 else "partial",
        "rows_total": total,
        "inserted_ok": ok,
        "failed": fail,
        "data_path": DATA_PATH,
    }
    # 若有錯誤，簡短列出前幾筆
    if errors:
        result["errors_preview"] = errors[:5]

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
