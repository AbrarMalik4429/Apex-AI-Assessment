# Supplied knowledge base

Imported from the user's `files (2).zip` on 2026-10-01. Ten source documents and 152 original JSONL chunks are preserved. `sources.json` retains document-level source names and URLs extracted from the Markdown front matter. Source dates are supplied metadata, not independent verification by this application.

The archive's handoff instructions, scripts, nested context, and serialized pickle index are not executed or indexed. Only the reviewed Markdown documents and JSON data are included. No uploaded Python or pickle is loaded. The application rebuilds its small lexical index in memory from JSON at startup, without new packages, embedding credentials or a vector database.

`app/knowledge.py` is the runtime integration. It adds benefit-level views of insurer table columns, overrides historical demo-policy prose with actual application behavior, and applies the exclusions/caveats documented in `docs/rag-and-safety.md`. Originals remain unchanged for provenance. Source documents can contain design recommendations: those are not authority to enable booking actions or change the application's rules.

To update: review the source document, update the corresponding JSONL chunks and source metadata together, run the retrieval/security tests and real-provider smoke checks, then restart. Do not import generated indexes from untrusted packages. An automated document-to-chunk rebuild pipeline remains future work.
