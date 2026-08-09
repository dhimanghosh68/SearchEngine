from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DocumentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    description: str = Field(default="", max_length=2000)
    content: str = Field(default="")


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    description: str = Field(default="", max_length=2000)
    content: str = Field(default="")


class DocumentResponse(BaseModel):
    id: str
    title: str
    url: str
    description: str
    content: str


class DocumentListResponse(BaseModel):
    page: int
    limit: int
    total: int
    results: list[DocumentResponse]


class BulkDocumentResponse(BaseModel):
    count: int
    ids: list[str]


class SearchResult(BaseModel):
    id: str
    score: float | None
    title: str
    url: str
    description: str
    content: str
    highlight: dict[str, list[str]] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    page: int
    limit: int
    total: int
    results: list[SearchResult]