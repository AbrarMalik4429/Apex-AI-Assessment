# RAG and knowledge-base requirements — implementation checkpoint

RAG is now integrated using the supplied knowledge base. See `rag-and-safety.md` for the implemented communication path and limitations.

## Direct RAG requirements

- Maintain a small, trusted knowledge base.
- Retrieve relevant material for knowledge questions.
- Prevent unsupported knowledge-base claims from being presented as facts.

## Functional areas that fit retrieval

- Preparation instructions for appointments or procedures.
- Insurance and general clinic questions.
- Explanations of clinic policies, with executable booking rules continuing to be enforced by Python.
- Escalation guidance where approved reference material exists; creating an escalation remains a separate operational action.

## Supporting requirements

Clarify ambiguous requests, return the required structured response, handle prompt injection and protect patient information. Missing or conflicting knowledge needs a defined fallback. Evaluation should include grounded answers, absent evidence, ambiguity and adversarial requests; the assessment's minimum evaluation coverage spans the whole service, not just retrieval. Model choice, operating cost and production considerations remain part of the overall assessment.

## Source-data boundary

The user supplied ten documents and 152 chunks in files (2).zip. Historical/demo content is qualified and procedural first aid is retained for review rather than served. Do not invent Apex policies, insurance coverage or clinical preparation instructions and present them as real clinic facts.
