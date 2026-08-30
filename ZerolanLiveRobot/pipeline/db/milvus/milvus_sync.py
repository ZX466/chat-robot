import json

import requests
from pydantic import BaseModel, Field
from zerolan.data.pipeline.milvus import MilvusInsert, MilvusInsertResult, MilvusQuery, MilvusQueryResult

from pipeline.base.base_sync import AbstractPipeline, AbstractPipelineConfig, DEFAULT_REQUEST_TIMEOUT


class MilvusDatabaseConfig(AbstractPipelineConfig):
    insert_url: str = Field(default="http://127.0.0.1:11000/milvus/insert",
                            description="The URL for inserting data into Milvus.")
    search_url: str = Field(default="http://127.0.0.1:11000/milvus/search",
                            description="The URL for searching data in Milvus.")


class MilvusSyncPipeline(AbstractPipeline):
    def __init__(self, config: MilvusDatabaseConfig):
        super().__init__(config)
        self.insert_url = config.insert_url
        self.search_url = config.search_url
        self._session = requests.Session()
        self._timeout = DEFAULT_REQUEST_TIMEOUT

    def _post(self, url: str, obj, return_type):
        if isinstance(obj, BaseModel):
            json_val = obj.model_dump()
        else:
            json_val = obj

        response = self._session.post(url=url, json=json_val, timeout=self._timeout)
        response.raise_for_status()

        json_val = response.json()
        if hasattr(return_type, "model_validate"):
            return return_type.model_validate(json_val)
        else:
            return json.loads(json_val)

    def insert(self, insert: MilvusInsert) -> MilvusInsertResult:
        return self._post(url=self.insert_url, obj=insert, return_type=MilvusInsertResult)

    def search(self, query: MilvusQuery) -> MilvusQueryResult:
        return self._post(url=self.search_url, obj=query, return_type=MilvusQueryResult)

    def close(self):
        self._session.close()
