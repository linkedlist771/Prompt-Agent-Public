from functools import lru_cache
from typing import Any, Dict, List

import chromadb
from loguru import logger

from prompt_agent.configs import DEFAULT_VECTOR_DB_NAME, VECTOR_DB_DIR

# # Add docs to the collection. Can also update and delete. Row-based API coming soon!
# collection.add(
#     documents=["This is document1", "This is document2"], # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
#     metadatas=[{"source": "notion"}, {"source": "google-docs"}], # filter on these!
#     ids=["doc1", "doc2"], # unique for each doc
# )
#
# # Query/search 2 most similar results. You can also .get by id
# results = collection.query(
#     query_texts=["This is a query document"],
#     n_results=2,
#     # where={"metadata_field": "is_equal_to_this"}, # optional filter
#     # where_document={"$contains":"search_string"}  # optional filter
# )


class PromptVectorDB(object):
    def __init__(self):
        # 但是这个数据库被存到哪里了？
        self.client = chromadb.PersistentClient(
            path=VECTOR_DB_DIR
        )  # default: all-MiniLM-L6-v2
        # 先不管垂类了，都用一个算了， 没什么关系反正。
        self.collection = self.client.get_or_create_collection(
            name=DEFAULT_VECTOR_DB_NAME
        )

    def add(self, *args, **kwargs):
        """
        We have enabled the collection_name in the query and add methods.
        """
        try:
            collection_name = kwargs.pop("collection_name", None)  # 只 pop 一次

            if isinstance(collection_name, str) and collection_name:
                # 使用 get_or_create_collection 确保 collection 存在
                collection = self.client.get_or_create_collection(name=collection_name)
            else:
                collection = self.collection

            collection.add(*args, **kwargs)
            return "OK, added"
        except Exception as e:
            return str(e)

    def query(self, *args, **kwargs):
        collection_name = kwargs.pop("collection_name", None)  # 只 pop 一次
        if isinstance(collection_name, str) and collection_name:
            collection = self.client.get_collection(name=collection_name)
        else:
            collection = self.collection

        return collection.query(*args, **kwargs)

    def count(self):
        return self.collection.count()

    def list_all(self):
        result = self.collection.peek(self.count())
        # 移除不可序列化的嵌入向量
        filtered_result = {
            "ids": result.get("ids", []),
            "documents": result.get("documents", []),
            "metadatas": result.get("metadatas", []),
            # 不包含 'embeddings' 字段
        }
        return filtered_result

    def list_collections(self) -> List[str]:
        # list
        # # collections: ['default']
        collections = self.client.list_collections()
        collection_names = [collection.name for collection in collections]
        return collection_names


@lru_cache()
def get_prompt_vector_db():
    return PromptVectorDB()


if __name__ == "__main__":
    from loguru import logger

    vector_db = get_prompt_vector_db()
    logger.info(f"list collections: {vector_db.list_collections()}")

    query = "Hello world"
    logger.info(f"rag results: {vector_db.query(query_texts=[query], n_results=3)}")

    all_docs = vector_db.list_all()
    logger.info(f"all docs: {all_docs}")
