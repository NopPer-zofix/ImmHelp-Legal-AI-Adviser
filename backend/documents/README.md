# Knowledge base layout

One folder per topic. **The folder name is the topic tag**: every PDF inside is ingested into
ChromaDB with `metadata.topic` set to the folder name, and `/ask` retrieves only from the
folder(s) the orchestrator routed the question to. See `../PROMPT_ROUTING.md`.

| Folder         | Topic label   | Topic prompt                   |
|----------------|---------------|--------------------------------|
| `visa/`        | `VISA`        | `system_prompt_visa.txt`       |
| `transport/`   | `TRANSPORT`   | `system_prompt_transport.txt`  |
| `real_estate/` | `REAL_ESTATE` | `system_prompt_realestate.txt` |
| `general/`     | `GENERAL`     | base prompt only               |

`general/` is also searched as a fallback for every topic, so cross-cutting material (cost of
living, banking, general relocation guides) goes there once and is reachable from any topic.

## Current contents

`visa/` holds everything the RAG model had so far — the MEDU2 student track, the MDW3
domestic-worker track, renewals and the visa application forms.

`transport/` and `real_estate/` have no source material yet. Those topics answer from the model's
general knowledge plus the guardrails written into their prompts until documents are added. Good
candidates to collect:

- **transport** — Road Transport Department licence-exchange leaflets, vehicle registration and
  import guides, MOT rules, the Highway Code, district bus operator fare tables.
- **real_estate** — Land Registry transfer-fee tables, the standard tenancy agreement, the Rent
  Control Law summary, the non-EU acquisition permission application, VAT-on-property guidance.

## Adding documents

1. Drop the PDF into the right folder. **Only `.pdf` is ingested** — the `.doc`/`.docx` files in
   `visa/` are reference forms and are not indexed. Convert them to PDF if they should be
   searchable.
2. Restart the server. New files are picked up on startup; files already indexed are skipped.
3. If you MOVE or RENAME a file, delete `chroma_db/` and restart — the old entry keeps the old
   path and would linger as a duplicate.
