---
title: PGVectorStore
---

`PGVectorStore` is an implementation of a LangChain vectorstore using `postgres` as the backend.

This guide goes over how to use the `PGVectorStore` API.

The code lives in an integration package called: [langchain-postgres](https://github.com/langchain-ai/langchain-postgres/).

## Setup

This package requires a PostgreSQL database with the `pgvector` extension.

You can run the following command to spin up a container for a `pgvector` enabled Postgres instance:

```shell
docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
```

### Install
Install the integration library, `langchain-postgres`.


```python
%pip install --upgrade --quiet  langchain-postgres
# This notebook also requires the following dependencies
%pip install --upgrade --quiet  langchain-core langchain-cohere sqlalchemy
```

### Set your Postgres values

Set your Postgres values to test the functionality in this notebook against a Postgres instance.


```python
# @title Set your values or use the defaults to connect to Docker { display-mode: "form" }
POSTGRES_USER = "langchain"  # @param {type: "string"}
POSTGRES_PASSWORD = "langchain"  # @param {type: "string"}
POSTGRES_HOST = "localhost"  # @param {type: "string"}
POSTGRES_PORT = "6024"  # @param {type: "string"}
POSTGRES_DB = "langchain"  # @param {type: "string"}
TABLE_NAME = "vectorstore"  # @param {type: "string"}
VECTOR_SIZE = 1024  # @param {type: "int"}
```

## Initialization

### PGEngine Connection Pool

One of the requirements and arguments to establish PostgreSQL as a vector store is a `PGEngine` object. The `PGEngine`  configures a shared connection pool  to your Postgres database. This is an industry best practice to manage number of connections and to reduce latency through cached database connections.

`PGVectorStore` can be used with the `asyncpg` and `psycopg3` drivers.

To create a `PGEngine` using `PGEngine.from_connection_string()` you need to provide:

1. `url` : Connection string using the `postgresql+asyncpg` driver.


**Note:** This tutorial demonstrates the async interface. All async methods have corresponding sync methods.


```python
# See docker command above to launch a Postgres instance with pgvector enabled.
CONNECTION_STRING = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}"
    f":{POSTGRES_PORT}/{POSTGRES_DB}"
)
# To use psycopg3 driver, set your connection string to `postgresql+psycopg://`
```


```python
from langchain_postgres import PGEngine

pg_engine = PGEngine.from_connection_string(url=CONNECTION_STRING)
```

To create a `PGEngine` using `PGEngine.from_engine()` you need to provide:

1. `engine` : An object of `AsyncEngine`


```python
from sqlalchemy.ext.asyncio import create_async_engine

# Create an SQLAlchemy Async Engine
engine = create_async_engine(
    CONNECTION_STRING,
)

pg_engine = PGEngine.from_engine(engine=engine)
```

### Initialize a table

The `PGVectorStore` class requires a database table. The `PGEngine` engine has a helper method `ainit_vectorstore_table()` that can be used to create a table with the proper schema for you.

See [Create a custom Vector Store](#create-a-custom-vector-store) or [Create a Vector Store using existing table](#create-a-vector-store-using-existing-table) for customizing the schema.


```python
await pg_engine.ainit_vectorstore_table(
    table_name=TABLE_NAME,
    vector_size=VECTOR_SIZE,
)
```

#### Optional Tip: 💡
You can also specify a schema name by passing `schema_name` wherever you pass `table_name`. Eg:

```python
SCHEMA_NAME="my_schema"

await pg_engine.ainit_vectorstore_table(
    table_name=TABLE_NAME,
    vector_size=768,
    schema_name=SCHEMA_NAME,    # Default: "public"
)
```

### Create an embedding class instance

You can use any [LangChain embeddings model](https://python.langchain.com/docs/integrations/text_embedding/).


```python
from langchain_cohere import CohereEmbeddings

embedding = CohereEmbeddings(model="embed-english-v3.0")
```

### Initialize a default PGVectorStore

Use the default table schema to connect to the vectorstore.

See [Create a custom Vector Store](#create-a-custom-vector-store) or [Create a Vector Store using existing table](#create-a-vector-store-using-existing-table) for customizing the schema.


```python
from langchain_postgres import PGVectorStore

store = await PGVectorStore.create(
    engine=pg_engine,
    table_name=TABLE_NAME,
    # schema_name=SCHEMA_NAME,
    embedding_service=embedding,
)
```

## Manage vector store

### Add documents

Add documents to the vector store. Metadata is stored in a JSON column, see "Create a custom Vector Store" to store metadata to be used for filters.


```python
import uuid

from langchain_core.documents import Document

docs = [
    Document(
        id=str(uuid.uuid4()),
        page_content="Red Apple",
        metadata={"description": "red", "content": "1", "category": "fruit"},
    ),
    Document(
        id=str(uuid.uuid4()),
        page_content="Banana Cavendish",
        metadata={"description": "yellow", "content": "2", "category": "fruit"},
    ),
    Document(
        id=str(uuid.uuid4()),
        page_content="Orange Navel",
        metadata={"description": "orange", "content": "3", "category": "fruit"},
    ),
]

await store.aadd_documents(docs)
```

### Add texts

Add text directly to the vectorstore, if not structured as a Document.


```python
import uuid

all_texts = ["Apples and oranges", "Cars and airplanes", "Pineapple", "Train", "Banana"]
metadatas = [{"len": len(t)} for t in all_texts]
ids = [str(uuid.uuid4()) for _ in all_texts]

await store.aadd_texts(all_texts, metadatas=metadatas, ids=ids)
```

### Delete documents

Documents can be deleted using ids.


```python
await store.adelete([ids[1]])
```

## Query vector store

### Search for documents

Use a natural language query to search for similar documents.


```python
query = "I'd like a fruit."
docs = await store.asimilarity_search(query)
print(docs)
```

### Search for documents by vector

Search for similar documents using a vector embedding.


```python
query_vector = embedding.embed_query(query)
docs = await store.asimilarity_search_by_vector(query_vector, k=2)
print(docs)
```

## Add a Index
Speed up vector search queries by applying a vector index. Learn more about [vector indexes](https://cloud.google.com/blog/products/databases/faster-similarity-search-performance-with-pgvector-indexes). 

Indexes will use a default index name if a name is not provided. To add multiple indexes, different index names are required.


```python
from langchain_postgres.v2.indexes import HNSWIndex, IVFFlatIndex

index = IVFFlatIndex()
await store.aapply_vector_index(index)

index = HNSWIndex(name="my-hnsw-index")
await store.aapply_vector_index(index)
```

Set index parameters to tune the index for optimal balance between recall and QPS.


```python
index = IVFFlatIndex(name="my-ivfflat", lists=120)
await store.aapply_vector_index(index)
```

### Re-index

Rebuild an index using the data stored in the index's table, replacing the old copy of the index. Some index types may require re-indexing after a considerable amount of new data is added.


```python
await store.areindex()  # Re-index using the default index name
await store.areindex("my-hnsw-index")  # Re-index using the index name
```

### Drop an index

Remove a vector index.


```python
await store.adrop_vector_index()  # Delete index using the default name
await store.adrop_vector_index("my-hnsw-index")  # Delete index using the index name
```

### Create a custom Vector Store

Customize the vectorstore with special column names or with custom metadata columns.

`ainit_vectorstore_table`
* Use fields `content_column`, `embedding_column`,`metadata_columns`, `metadata_json_column`, `id_column` to rename the columns. 
* Use the `Column` class to create custom id or metadata columns. A Column is defined by a name and data type. Any Postgres [data type](https://www.postgresql.org/docs/current/datatype.html) can be used.
* Use `store_metadata` to create a JSON column to store extra metadata.

#### Optional Tip: 💡
To use non-uuid ids, you must customize the id column:
```python
await pg_engine.ainit_vectorstore_table(
    ...,
    id_column=Column(name="langchain_id", data_type="INTEGER")
)
```

`PGVectorStore`
* Use fields `content_column`, `embedding_column`,`metadata_columns`, `metadata_json_column`, `id_column` to rename the columns. 
* `ignore_metadata_columns` to ignore columns that should not be used for Document metadata. This is helpful when using a preexisting table, where all data columns are not necessary.
* Use a different `distance_strategy` for the similarity calculation during vector search.
* Use `index_query_options` to tune local index parameters during vector search.


```python
from langchain_postgres import Column

# Set table name
TABLE_NAME = "vectorstore_custom"
# SCHEMA_NAME = "my_schema"

await pg_engine.ainit_vectorstore_table(
    table_name=TABLE_NAME,
    # schema_name=SCHEMA_NAME,
    vector_size=VECTOR_SIZE,
    metadata_columns=[Column("len", "INTEGER")],
)


# Initialize PGVectorStore
custom_store = await PGVectorStore.create(
    engine=pg_engine,
    table_name=TABLE_NAME,
    # schema_name=SCHEMA_NAME,
    embedding_service=embedding,
    metadata_columns=["len"],
)
```

### Search for documents with metadata filter

A Vector Store can take advantage of relational data to filter similarity searches. The vectorstore supports a set of filters that can be applied against the metadata fields of the documents. See the [migration guide](https://github.com/langchain-ai/langchain-postgres/blob/main/examples/migrate_pgvector_to_pgvectorstore.ipynb) for details on how to migrate to use metadata columns.

`PGVectorStore` currently supports the following operators and all Postgres data types.

| Operator  | Meaning/Category        |
|-----------|-------------------------|
| $eq       | Equality (==)           |
| $ne       | Inequality (!=)         |
| $lt       | Less than (\<)           |
| $lte      | Less than or equal (\<=) |
| $gt       | Greater than (>)        |
| $gte      | Greater than or equal (>=) |
| $in       | Special Cased (in)      |
| $nin      | Special Cased (not in)  |
| $between  | Special Cased (between) |
| $exists   | Special Cased (is null) |
| $like     | Text (like)             |
| $ilike    | Text (case-insensitive like) |
| $and      | Logical (and)           |
| $or       | Logical (or)            |


```python
import uuid

docs = [
    Document(
        id=str(uuid.uuid4()),
        page_content="Red Apple",
        metadata={"description": "red", "content": "1", "category": "fruit"},
    ),
    Document(
        id=str(uuid.uuid4()),
        page_content="Banana Cavendish",
        metadata={"description": "yellow", "content": "2", "category": "fruit"},
    ),
    Document(
        id=str(uuid.uuid4()),
        page_content="Orange Navel",
        metadata={"description": "orange", "content": "3", "category": "fruit"},
    ),
]

await custom_store.aadd_documents(docs)

# Use a dictionary filter on search
docs = await custom_store.asimilarity_search(query, filter={"content": {"$gte": 1}})

print(docs)
```

### Create a Vector Store using existing table

A Vector Store can be built up on an existing table.

Assuming there's a pre-existing table in PG DB: `products`, which stores product details for an eComm venture.

<Accordion title="Click for Table Schema Details">
### SQL query for table creation

```text
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price_usd DECIMAL(10, 2) NOT NULL,
    category VARCHAR(255),
    quantity INT DEFAULT 0,
    sku VARCHAR(255) UNIQUE NOT NULL,
    image_url VARCHAR(255),
    metadata JSON,
    embed vector(768) DEFAULT NULL -- vector dimensions depends on the embedding model
);
```

### Insertion of records

```text
INSERT INTO
products (name,
  description,
  price_usd,
  category,
  quantity,
  sku,
  image_url,
  METADATA,
  embed)
VALUES
('Laptop', 'High-performance gaming laptop', 1200.00, 'Electronics', 10, 'SKU12345', 'https://example.com/laptop.jpg', '{"category" : "Electronics", "name" : "Laptop", "description" : "High-performance gaming laptop"}', ARRAY[0.028855365,-0.012488421,...]),
('Smartphone', 'Latest model with high-resolution camera', 800.00, 'Electronics', 15, 'SKU12346', 'https://example.com/smartphone.jpg', '{"category" : "Electronics", "name" : "Smartphone", "description" : "Latest model with high-resolution camera"}', ARRAY[0.031757303,-0.030950155,...]),
('Coffee Maker', 'Brews coffee in under 5 minutes', 99.99, 'Kitchen Appliances', 20, 'SKU12347', 'https://example.com/coffeemaker.jpg', '{"category" : "Kitchen Appliances", "name" : "Coffee Maker", "description" : "Brews coffee in under 5 minutes"}', ARRAY[0.025002815,-0.052869678,...]),
('Bluetooth Headphones', 'Noise cancelling, over the ear headphones', 250.00, 'Accessories', 5, 'SKU12348', 'https://example.com/headphones.jpg', '{"category" : "Accessories", "name" : "Bluetooth Headphones", "description" : "Noise cancelling, over the ear headphones"}', ARRAY[0.022783848,-0.057248034,...]),
('Backpack', 'Waterproof backpack with laptop compartment', 59.99, 'Accessories', 30, 'SKU12349', 'https://example.com/backpack.jpg', '{"category" : "Accessories", "name" : "Backpack", "description" : "Waterproof backpack with laptop compartment"}', ARRAY[-0.0028279827,-0.02903348,...]);
```
</Accordion>

Here is how this table mapped to `PGVectorStore`:

- **`id_column="product_id"`**: ID column uniquely identifies each row in the products table.

- **`content_column="description"`**: The `description` column contains text descriptions of each product. This text is used by the `embedding_service` to create vectors that go in embedding_column and represent the semantic meaning of each description.

- **`embedding_column="embed"`**: The `embed` column stores the vectors created from the product descriptions. These vectors are used to find products with similar descriptions.

- **`metadata_columns=["name", "category", "price_usd", "quantity", "sku", "image_url"]`**: These columns are treated as metadata for each product. Metadata provides additional information about a product, such as its name, category, price, quantity available, SKU (Stock Keeping Unit), and an image URL. This information is useful for displaying product details in search results or for filtering and categorization.

- **`metadata_json_column="metadata"`**: The `metadata` column can store any additional information about the products in a flexible JSON format. This allows for storing varied and complex data that doesn't fit into the standard columns.



```python
# Set an existing table name
TABLE_NAME = "products"
# SCHEMA_NAME = "my_schema"

# Initialize PGVectorStore
custom_store = await PGVectorStore.create(
    engine=pg_engine,
    table_name=TABLE_NAME,
    # schema_name=SCHEMA_NAME,
    embedding_service=embedding,
    # Connect to existing VectorStore by customizing below column names
    id_column="product_id",
    content_column="description",
    embedding_column="embed",
    metadata_columns=["name", "category", "price_usd", "quantity", "sku", "image_url"],
    metadata_json_column="metadata",
)
```
Note: 

1. Optional: If the `embed` column is newly created or has different dimensions than supported by embedding model, it is required to one-time add the embeddings for the old records, like this: 

    `ALTER TABLE products ADD COLUMN embed vector(768) DEFAULT NULL`

1. For new records, added via `VectorStore` embeddings are automatically generated.

## Clean up

**⚠️ WARNING: this can not be undone**

Drop the vector store table.


```python
await pg_engine.adrop_table(TABLE_NAME)
```

## Usage for retrieval-augmented generation

For guides on how to use this vector store for retrieval-augmented generation (RAG), see the following sections:

- [Tutorials](/oss/tutorials/rag)
- [How-to: Question and answer with RAG](https://python.langchain.com/docs/how_to/#qa-with-rag)
- [Retrieval conceptual docs](https://python.langchain.com/docs/concepts/retrieval)

## API reference

For detailed documentation of all VectorStore features and configurations head to the API reference: https://python.langchain.com/api_reference/postgres/v2/langchain_postgres.v2.vectorstores.PGVectorStore.html
