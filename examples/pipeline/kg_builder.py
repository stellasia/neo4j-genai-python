#  Copyright (c) "Neo4j"
#  Neo4j Sweden AB [https://neo4j.com]
#  #
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  #
#      https://www.apache.org/licenses/LICENSE-2.0
#  #
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from __future__ import annotations

import asyncio
from typing import Any

from neo4j_genai.pipeline import Component, DataModel
from pydantic import BaseModel


class DocumentChunkModel(DataModel):
    chunks: list[str]


class DocumentChunker(Component):
    async def run(self, text: str) -> DocumentChunkModel:
        chunks = [t.strip() for t in text.split(".") if t.strip()]
        return DocumentChunkModel(chunks=chunks)


class SchemaModel(DataModel):
    data_schema: str


class SchemaBuilder(Component):
    async def run(self, schema: str) -> SchemaModel:
        return SchemaModel(data_schema=schema)


class EntityModel(BaseModel):
    label: str
    properties: dict[str, str]


class ERModel(DataModel):
    entities: list[EntityModel]
    relations: list[EntityModel]


class ERExtractor(Component):
    async def _process_chunk(self, chunk: str, schema: str) -> dict[str, Any]:
        return {
            "entities": [{"label": "Person", "properties": {"name": "John Doe"}}],
            "relations": [],
        }

    async def run(self, chunks: list[str], schema: str) -> ERModel:
        tasks = [self._process_chunk(chunk, schema) for chunk in chunks]
        result = await asyncio.gather(*tasks)
        merged_result: dict[str, Any] = {"entities": [], "relations": []}
        for res in result:
            merged_result["entities"] += res["entities"]
            merged_result["relations"] += res["relations"]
        return ERModel(
            entities=merged_result["entities"], relations=merged_result["relations"]
        )


class WriterModel(DataModel):
    status: str
    entities: list[EntityModel]
    relations: list[EntityModel]


class Writer(Component):
    async def run(
        self, entities: list[dict[str, Any]], relations: list[dict[str, Any]]
    ) -> WriterModel:
        return WriterModel(
            status="OK",
            entities=[EntityModel(**e) for e in entities],
            relations=[EntityModel(**r) for r in relations],
        )


if __name__ == "__main__":
    from neo4j_genai.pipeline import Pipeline

    pipe = Pipeline()
    pipe.add_component("chunker", DocumentChunker())
    pipe.add_component("schema", SchemaBuilder())
    pipe.add_component("extractor", ERExtractor())
    pipe.add_component("writer", Writer())
    pipe.connect("chunker", "extractor", input_config={"chunks": "chunker.chunks"})
    pipe.connect("schema", "extractor", input_config={"schema": "schema.data_schema"})
    pipe.connect(
        "extractor",
        "writer",
        input_config={
            "entities": "extractor.entities",
            "relations": "extractor.relations",
        },
    )

    pipe_inputs = {
        "chunker": {
            "text": """Graphs are everywhere.
            GraphRAG is the future of Artificial Intelligence.
            Robots are already running the world."""
        },
        "schema": {"schema": "Person OWNS House"},
    }
    # print(pipe.run_all(pipe_inputs))
    print(asyncio.run(pipe.run(pipe_inputs)))
