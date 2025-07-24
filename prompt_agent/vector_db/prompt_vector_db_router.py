import asyncio
from functools import partial
from hashlib import md5
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request

from prompt_agent.schemas import DocumentUploadRequest
from prompt_agent.vector_db.prompt_vector_db import get_prompt_vector_db

router = APIRouter()

prompt_vector_db = get_prompt_vector_db()


@router.post("/add")
# async def add(prompt_template: str):
async def add(document_upload_request: DocumentUploadRequest):
    # 这是最简单的写法。
    # count = prompt_vector_db.count()
    hash_id = md5(document_upload_request.prompt_template.encode("utf-8")).hexdigest()
    ids = [hash_id]  # 删除是用id山东

    collection_name = document_upload_request.collection_name
    if collection_name:
        # 如果设置了这个
        assert (
            collection_name in prompt_vector_db.list_collections()
        ), f"collection {collection_name} not in collections: {prompt_vector_db.list_collections()}"

    # return prompt_vector_db.add(
    #     documents=[document_upload_request.prompt_template],
    #     ids=ids,
    #     collection_name=collection_name,
    # )
    add_partial = partial(
        prompt_vector_db.add,
        documents=[document_upload_request.prompt_template],
        ids=ids,
        collection_name=collection_name,
    )
    return await asyncio.to_thread(add_partial)


@router.get("/list_collections")
async def list_collections():
    """
    列出所有的collection
    """
    # return prompt_vector_db.list_collections()
    return await asyncio.to_thread(prompt_vector_db.list_collections)


@router.get("/")
async def _():
    return prompt_vector_db.list_all()


# delete， 暂时不写了。 list。
