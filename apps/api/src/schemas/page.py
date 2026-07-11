from pydantic import BaseModel, Field


class PageInfo(BaseModel):
    pageSize: int = Field(ge=1)
    currentPage: int = Field(ge=0)
    totalRecord: int = Field(ge=0)
