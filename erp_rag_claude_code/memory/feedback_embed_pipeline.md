---
name: Embed pipeline — chunk first, then embed per chunk
description: embedding must operate on individual chunks with their metadata, not on the whole asset
type: feedback
---

The embedding pipeline must follow this order:
1. Chunk the asset using its ChunkStrategy → produces `list[Chunk]` (each with `.text` + `.metadata`)
2. For EACH chunk: embed `chunk.text` and store the vector **with `chunk.metadata` attached**
3. The vector count = number of chunks embedded

**Why:** Embedding the whole asset as one vector loses the section/article/table metadata
that makes retrieval useful. Each chunk is an independent retrieval unit.

**How to apply:** The `EmbedAssetUseCase` must receive both a `chunker` callable
(returns `list[Chunk]`) and an `embedder` callable (takes `list[Chunk]` + context,
stores vectors per chunk, returns total vector count). Never collapse chunking and
embedding into one opaque callable.
