from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "mock-gpt-model"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = False

    # NEW: rag support
    enable_retrival: Optional[bool] = Field(
        default=False, description="Enable retrieval-augmented generation (RAG) support"
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="Name of the vector database collection to use for RAG",
    )
