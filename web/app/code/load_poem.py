# -*- coding: utf-8 -*-
import os
import re
import csv
import sys
import json
import unicodedata as ud
import datetime
import configparser
import pymongo
from pymongo import UpdateOne

config = configparser.ConfigParser()
config.read('/app/config.env')

def get_root_mongodb_url():
    user = config['MongoDB']['MONGO_ROOT_USERNAME']
    pwd  = config['MongoDB']['MONGO_ROOT_PASSWORD']
    host = config['MongoDB']['MONGO_HOST']
    port = config['MongoDB']['MONGO_PORT']
    return f"mongodb://{user}:{pwd}@{host}:{port}/?authSource=admin"

DATABASE = config['MongoDB']['MONGO_DATABASE']
DATA_PATH = '/app/web/app/ori_data/poem.csv'
COLLECTION_NAME = 'poem'
BATCH_SIZE = 1000

CTRL_RE = re.compile(r'[\x00-\x1F\x7F]')
SPACE_RE = re.compile(r'\s+')
CJK_RE = re.compile(r'[\u4E00-\u9FFF]')

def strip_ctrl(s: str | None) -> str:
    return CTRL_RE.sub('', s or '')

def normalize_text(s: str) -> str:
    """全半形統一 + 空白正規化"""
    s = strip_ctrl(s)
    s = ud.normalize('NFKC', s)
    s = SPACE_RE.sub(' ', s).strip()
    return s

def safe_int(x):
    try:
        return int(str(x).strip())
    except Exception:
        return None

def gen_search_text(title, form, era, author, content):
    parts = [p for p in [title, form, era, author, content] if p]
    text = ' '.join(parts)
    return normalize_text(text)

def gen_ngrams_bi(s: str):
    """產生中文字二連詞陣列"""
    s = re.sub(r'\s+', '', s)
    grams = []
    for i in range(len(s) - 1):
        a, b = s[i], s[i+1]
        if CJK_RE.match(a) and CJK_RE.match(b):
            grams.append(a + b)
    # 去重保序
    seen, uniq = set(), []
    for g in grams:
        if g not in seen:
            seen.add(g)
            uniq.append(g)
    return uniq

# -------------------------
# Mongo 連線
# -------------------------
def get_collection():
    url = get_root_mongodb_url()
    client = pymongo.MongoClient(url)
    db = client[DATABASE]
    coll = db[COLLECTION_NAME]
    return client, coll

# -------------------------
# 主流程
# -------------------------
def main():
    if not os.path.exists(DATA_PATH):
        sys.stderr.write(f"[error] data file not found: {DATA_PATH}\n")
        sys.exit(1)

    client, coll = get_collection()
    now = datetime.datetime.utcnow()
    total, written = 0, 0
    ops = []

    with open(DATA_PATH, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            total += 1
            ID = safe_int(r.get('編號'))
            if ID is None:
                continue

            title = strip_ctrl(r.get('題名') or None)
            if title == '*':  # 去掉無意義標題
                title = None

            form = strip_ctrl(r.get('型式') or None)
            era = strip_ctrl(r.get('朝代') or None)
            author = strip_ctrl(r.get('作者') or None)
            content_raw = strip_ctrl(r.get('內容') or '')
            content_norm = normalize_text(content_raw)

            search_text = gen_search_text(title, form, era, author, content_norm)
            ngrams_bi = gen_ngrams_bi(search_text)
            meta = {'chars': len(content_norm)}

            doc = {
                'ID': ID,
                'title': title,
                'form': form,
                'era': era,
                'author': author,
                'content_raw': content_raw,
                'content_norm': content_norm,
                'search_text': search_text,
                'ngrams_bi': ngrams_bi,
                'meta': meta,
                'created_date': now,
                'updated_date': now
            }

            ops.append(
                UpdateOne({'ID': ID}, {'$set': doc}, upsert=True)
            )

            if len(ops) >= BATCH_SIZE:
                res = coll.bulk_write(ops, ordered=False)
                written += res.upserted_count + res.modified_count
                ops = []

    if ops:
        res = coll.bulk_write(ops, ordered=False)
        written += res.upserted_count + res.modified_count

    client.close()

    print(json.dumps({
        'status': 'ok',
        'database': DATABASE,
        'collection': COLLECTION_NAME,
        'rows_total': total,
        'docs_written_or_modified': written,
        'data_path': DATA_PATH
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
