# Skill maintenance

This repository is the source of truth for `ai-vfx-local-post`. Runtime files are SKILL.md, agents/, assets/, references/, and scripts/. Keep project media, live task records, credentials and generated caches outside Git.

Changes should come from demonstrated workflow failures or explicit user requirements. Preserve theme isolation, per-batch generation authorization, original product geometry, and separate technical/visual/user acceptance. Historical project values are examples, not new defaults.

For edits, use skill-creator and writing-for-agents. Run the skill validator when available, local Markdown-link checks, JSON parsing, and `python -B -m unittest discover -s tests -v`. Exercise new CLI paths, including failure behavior. Geometry input assertions do not establish pixel or normal-speed validation.

Before syncing an installed copy, compare it with the repository snapshot; preserve unrelated local edits. Verify hashes after copying the runtime file allowlist. Publishing requires user authorization for the intended owner and visibility.

This repository is intended for public maintenance. Use anonymous examples and project-relative paths. Before public publication, scan all reachable history for credentials and inspect metadata, local usernames/paths, private task identifiers and client-specific references. Keep audit reports and private backups outside tracked files. A clean current tree does not sanitize older commits.
