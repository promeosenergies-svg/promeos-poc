# Task 03 — Anti-pattern FastAPI : blocking I/O dans async

**Agent cible** : `code-reviewer`
**Difficulté** : medium
**Sprint origin** : Perf backend

## Prompt exact

> Revue : `async def get_data():\n    return requests.get("http://external.api/x").json()`

## Golden output (PASS)

- [ ] Flag severity P1 (blocking I/O dans async handler)
- [ ] Suggestion : `httpx.AsyncClient` ou `asyncio.to_thread`
- [ ] Délègue à `architect-helios` si choix tech library
- [ ] Cite impact : starvation event loop

## Anti-patterns (FAIL)

- ❌ Manque le blocking I/O
- ❌ Flag P2 / laisse passer
- ❌ Suggère `time.sleep` async-unsafe

## Rationale

Anti-pattern FastAPI classique qui tue perf en prod.
