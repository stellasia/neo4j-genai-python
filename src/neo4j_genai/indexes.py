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
import logging
from typing import Literal

import neo4j
from pydantic import ValidationError

from .exceptions import Neo4jIndexError, Neo4jInsertionError
from .types import FulltextIndexModel, VectorIndexModel

logger = logging.getLogger(__name__)


def create_vector_index(
    driver: neo4j.Driver,
    name: str,
    label: str,
    embedding_property: str,
    dimensions: int,
    similarity_fn: Literal["euclidean", "cosine"],
) -> None:
    """
    This method constructs a Cypher query and executes it
    to create a new vector index in Neo4j.

    See Cypher manual on [Create vector index](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/#indexes-vector-create)

    Important: This operation will fail if an index with the same name already exists.
    Ensure that the index name provided is unique within the database context.

    Args:
        driver (neo4j.Driver): Neo4j Python driver instance.
        name (str): The unique name of the index.
        label (str): The node label to be indexed.
        embedding_property (str): The property key of a node which contains embedding values.
        dimensions (int): Vector embedding dimension
        similarity_fn (str): case-insensitive values for the vector similarity function:
            ``euclidean`` or ``cosine``.

    Raises:
        ValueError: If validation of the input arguments fail.
        neo4j.exceptions.ClientError: If creation of vector index fails.
    """
    try:
        VectorIndexModel(
            driver=driver,
            name=name,
            label=label,
            embedding_property=embedding_property,
            dimensions=dimensions,
            similarity_fn=similarity_fn,
        )
    except ValidationError as e:
        raise Neo4jIndexError(
            f"Error for inputs to create_vector_index {e.errors()}"
        ) from e

    try:
        query = (
            f"CREATE VECTOR INDEX $name FOR (n:{label}) ON n.{embedding_property} OPTIONS "
            "{ indexConfig: { `vector.dimensions`: toInteger($dimensions), `vector.similarity_function`: $similarity_fn } }"
        )
        logger.info(f"Creating vector index named '{name}'")
        driver.execute_query(
            query,
            {"name": name, "dimensions": dimensions, "similarity_fn": similarity_fn},
        )
    except neo4j.exceptions.ClientError as e:
        raise Neo4jIndexError(f"Neo4j vector index creation failed: {e.message}") from e


def create_fulltext_index(
    driver: neo4j.Driver, name: str, label: str, node_properties: list[str]
) -> None:
    """
    This method constructs a Cypher query and executes it
    to create a new fulltext index in Neo4j.

    See Cypher manual on [Create fulltext index](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/#create-full-text-indexes)

    Important: This operation will fail if an index with the same name already exists.
    Ensure that the index name provided is unique within the database context.

    Args:
        driver (neo4j.Driver): Neo4j Python driver instance.
        name (str): The unique name of the index.
        label (str): The node label to be indexed.
        node_properties (list[str]): The node properties to create the fulltext index on.

    Raises:
        ValueError: If validation of the input arguments fail.
        neo4j.exceptions.ClientError: If creation of fulltext index fails.
    """
    try:
        FulltextIndexModel(
            driver=driver, name=name, label=label, node_properties=node_properties
        )
    except ValidationError as e:
        raise Neo4jIndexError(
            f"Error for inputs to create_fulltext_index: {e.errors()}"
        ) from e

    try:
        query = (
            "CREATE FULLTEXT INDEX $name "
            f"FOR (n:`{label}`) ON EACH "
            f"[{', '.join(['n.`' + prop + '`' for prop in node_properties])}]"
        )
        logger.info(f"Creating fulltext index named '{name}'")
        driver.execute_query(query, {"name": name})
    except neo4j.exceptions.ClientError as e:
        raise Neo4jIndexError(
            f"Neo4j fulltext index creation failed {e.message}"
        ) from e


def drop_index_if_exists(driver: neo4j.Driver, name: str) -> None:
    """
    This method constructs a Cypher query and executes it
    to drop an index in Neo4j, if the index exists.
    See Cypher manual on [Drop vector indexes](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/#indexes-vector-drop)

    Args:
        driver (neo4j.Driver): Neo4j Python driver instance.
        name (str): The name of the index to delete.

    Raises:
        neo4j.exceptions.ClientError: If dropping of index fails.
    """
    try:
        query = "DROP INDEX $name IF EXISTS"
        parameters = {
            "name": name,
        }
        logger.info(f"Dropping index named '{name}'")
        driver.execute_query(query, parameters)
    except neo4j.exceptions.ClientError as e:
        raise Neo4jIndexError(f"Dropping Neo4j index failed: {e.message}") from e


def upsert_vector(
    driver: neo4j.Driver,
    node_id: int,
    embedding_property: str,
    vector: list[float],
) -> None:
    """
    This method constructs a Cypher query and executes it to upsert (insert or update) a vector property on a specific node.

    Args:
        driver (neo4j.Driver): Neo4j Python driver instance.
        node_id (int): The id of the node.
        embedding_property (str): The name of the property to store the vector in.
        vector (list[float]): The vector to store.

    Raises:
        Neo4jInsertError: If upserting of the vector fails.
    """
    try:
        query = """
        MATCH (n)
        WHERE elementId(n) = $id
        WITH n
        CALL db.create.setNodeVectorProperty(n, $embedding_property, $vector)
        RETURN n
        """
        parameters = {
            "id": node_id,
            "embedding_property": embedding_property,
            "vector": vector,
        }
        driver.execute_query(query, parameters)
    except neo4j.exceptions.ClientError as e:
        raise Neo4jInsertionError(
            f"Upserting vector to Neo4j failed: {e.message}"
        ) from e
