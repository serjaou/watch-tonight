# Harness Log: `2026-11-25` · Windows · Claude Code (`feat-018` follow-up / `feat-030` prep) — A database password printed into the session

- **Finding:** To learn whether `MONGODB_URI` in `.env` points to a local or a cloud database, the agent ran `grep "^MONGODB_URI=" .env | sed ...` meant to keep only the scheme. The `sed` patterns didn't match the whole line, so the session output showed the URI with the Atlas M0 database user's name and password. Nothing was committed or sent to another service, but the credential was in the session transcript. The owner was told at once and asked to rotate the password.
- **Layer:** `environment`.
- **Root cause:** Inspecting a secret-bearing line with a text filter that prints the line when the pattern fails. A filter that "removes the secret" fails open; one that "prints only the safe part" fails closed.
- **Harness change:** `docs/conventions.md` gets a rule: never print `.env` lines or values, not even filtered; to learn something about a URI, parse it and print only the safe part (e.g. `urllib.parse.urlsplit(uri).scheme` and whether the host ends in `mongodb.net`), or check only that the variable exists (`grep -c '^NAME=' .env`).
- **Also found:** `MONGODB_URI` is the cloud M0 cluster (from spike 09). Part 2 (`feat-030`) must not read it by default, or a seed run could write to the cloud database; its spec uses a separate local-only variable.
- **Lesson:** With secrets, write the command so that a mistake prints nothing: select the safe field, never subtract the secret.
