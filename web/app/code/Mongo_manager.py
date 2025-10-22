import pymongo
from pymongo import TEXT
from pymongo.errors import OperationFailure
import configparser
import datetime
from urllib.parse import quote_plus
import re

config = configparser.ConfigParser()
config.read('/app/config.env')

class MongoManager:
    def __init__(self):
        self.url = self._get_root_mongodb_url()
        self.client = pymongo.MongoClient(self.url)
        self.db = self.client[config['MongoDB']['MONGO_DATABASE']]
        self.poem_collection = self.db['poem']

    def _get_root_mongodb_url(self):
        user = quote_plus(config['MongoDB']['MONGO_ROOT_USERNAME'])
        pwd  = quote_plus(config['MongoDB']['MONGO_ROOT_PASSWORD'])
        host = config['MongoDB']['MONGO_HOST']
        port = config['MongoDB']['MONGO_PORT']
        return f"mongodb://{user}:{pwd}@{host}:{port}/?authSource=admin"

    def close(self):
        self.client.close()

    def insert_poem(self, ID, title, form, era, author, content_raw, content_norm, search_text, ngrams_bi, meta):
        created_date = datetime.datetime.now()
        updated_date = datetime.datetime.now()

        try:
            self.poem_collection.insert_one({
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
                'created_date': created_date,
                'updated_date': updated_date
            })
            return True
        except Exception as e:
            raise Exception(f"Error inserting poem: {e}")
            return False

    def del_poem(self, ID):
        try:
            self.poem_collection.delete_one({
                'ID': ID
            })
        except Exception as e:
            raise Exception(f"Error deleting poem: {e}")

    def get_poem(self, ID):
        try:
            return self.poem_collection.find_one({
                'ID': ID
            })
        except Exception as e:
            raise Exception(f"Error getting poem: {e}")
    
    def update_poem(self, update_dic):
        update_date = datetime.datetime.now()
        try:
            self.poem_collection.update_one({
                'ID': update_dic['ID']
            }, {
                '$set': update_dic
            })
        except Exception as e:
            raise Exception(f"Error updating poem: {e}")

    def search_by_title(self, title):
        try:
            return self.poem_collection.find({
                'title': title
            })
        except Exception as e:
            raise Exception(f"Error searching by title: {e}")
    
    def search_by_author(self, author):
        try:
            return self.poem_collection.find({
                'author': author
            })
        except Exception as e:
            raise Exception(f"Error searching by author: {e}")
    
    def search_by_form(self, form):
        try:
            return self.poem_collection.find({
                'form': form
            })
        except Exception as e:
            raise Exception(f"Error searching by form: {e}")

    # ---------- 建索引 ----------
    def ensure_indexes(self):
        coll = self.poem_collection
        # 唯一鍵（依你的資料而定）
        coll.create_index([('ID', pymongo.ASCENDING)], unique=True, name='uid_ID')

        # 文字索引：一次把需要的欄位列齊；中文常用 default_language="none"
        # 同一個集合只能有一個 text index；若之前建過其他 text index，請先 drop 再建。
        try:
            coll.create_index(
                [('title', TEXT), ('author', TEXT), ('search_text', TEXT)],
                name='text_idx_zh',
                default_language='none',
                weights={'title': 10, 'author': 5, 'search_text': 3}
            )
        except OperationFailure as e:
            # 如果已存在不同結構的 text index，會報錯
            raise Exception(
                f"建立 text index 失敗：{e}. 請確認集合中只有一個 text index，必要時先 drop 再重建。"
            )

        # 常見過濾索引
        coll.create_index([('form', pymongo.ASCENDING)], name='idx_form')
        coll.create_index([('era', pymongo.ASCENDING)], name='idx_era')

        # 中文 fallback 的 n-gram 陣列索引
        coll.create_index([('ngrams_bi', pymongo.ASCENDING)], name='idx_bigrams')

        # 其他輔助
        coll.create_index([('created_date', pymongo.ASCENDING)], name='idx_created')
        coll.create_index([('updated_date', pymongo.ASCENDING)], name='idx_updated')
        coll.create_index([('content_norm', pymongo.ASCENDING)], name='idx_content_norm')
        coll.create_index([('search_text', pymongo.ASCENDING)], name='idx_search_text')

    # ---------- 全文檢索主角：text -> ngram -> regex 三段式 ----------
    def search_text(self, q: str,
                    era: str | None = None,
                    form: str | None = None,
                    author: str | None = None,
                    page: int = 1,
                    size: int = 10):
        """
        先用 $text + textScore 排序；沒命中或語言不支援時，走 ngram 粗篩再 regex 精修。
        回傳: { 'used': 'text'|'ngram+regex'|'regex', 'total': int, 'items': [docs...] }
        """
        if not q:
            return {'used': 'none', 'total': 0, 'items': []}

        page = max(int(page), 1)
        size = min(max(int(size), 1), 100)
        skip = (page - 1) * size

        base = {}
        if era: base['era'] = era
        if form: base['form'] = form
        if author: base['author'] = author

        coll = self.poem_collection

        # 1) $text（首選）
        try:
            text_filter = base | {'$text': {'$search': q}}
            total = coll.count_documents(text_filter)
            if total > 0:
                cur = (coll.find(
                        text_filter,
                        {
                            'score': {'$meta': 'textScore'},
                            'ID': 1, 'title': 1, 'author': 1, 'era': 1, 'form': 1, 'content_raw': 1
                        }
                    )
                    .sort([('score', {'$meta': 'textScore'})])
                    .skip(skip).limit(size))
                return {'used': 'text', 'total': total, 'items': list(cur)}
        except OperationFailure:
            # 沒有 text index 或結構不符時會進來
            pass

        # 2) n-gram + 3) regex fallback（中文常用）
        bigrams = self._bigrams_zh(q)
        if bigrams:
            rough = base | {'ngrams_bi': {'$in': bigrams}}
            # 多抓一些候選，再用 regex 精修
            candidates = list(coll.find(
                rough, {'ID':1,'title':1,'author':1,'era':1,'form':1,'content_raw':1}
            ).skip(skip).limit(size * 3))
            rx = re.compile(re.escape(q))
            filtered = [d for d in candidates if rx.search((d.get('title') or '') + (d.get('content_raw') or ''))]
            return {
                'used': 'ngram+regex',
                'total': len(filtered),         # 粗估；若要準確 total，可分兩階段統計
                'items': filtered[:size]
            }

        # 最後手段：純 regex（效能較差）
        regex_filter = base | {
            '$or': [
                {'title': {'$regex': re.escape(q)}},
                {'content_raw': {'$regex': re.escape(q)}}
            ]
        }
        total = coll.count_documents(regex_filter)
        cur = coll.find(
            regex_filter, {'ID':1,'title':1,'author':1,'era':1,'form':1,'content_raw':1}
        ).skip(skip).limit(size)
        return {'used': 'regex', 'total': total, 'items': list(cur)}

    # ---------- 小工具：中文 bigram ----------
    def _bigrams_zh(self, s: str):
        CJK = re.compile(r'[\u3400-\u9FFF\uF900-\uFAFF]')
        buf, out = [], []
        for ch in s:
            if CJK.match(ch): buf.append(ch)
            else:
                if len(buf) >= 2:
                    out += [buf[i] + buf[i+1] for i in range(len(buf)-1)]
                buf = []
        if len(buf) >= 2:
            out += [buf[i] + buf[i+1] for i in range(len(buf)-1)]
        # 去重保序
        seen, uniq = set(), []
        for g in out:
            if g not in seen:
                seen.add(g)
                uniq.append(g)
        return uniq