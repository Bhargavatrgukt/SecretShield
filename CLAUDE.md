# SecretShield: context for Claude

## About this project
- Personal portfolio project: a tool that finds leaked passwords and keys in Git repos, including old history.
- The full plan is in docs/DESIGN.md. Read it before starting any step.
- It is built in 4 stages: (1) CLI scanner + GitHub + GitHub Actions, (2) FastAPI + PostgreSQL, (3) Docker, (4) GitHub webhook + PR comments.
- Platform: GitHub and GitHub Actions. Not GitLab.
- Python 3.11+ (installed locally: 3.11.8).

## About the user and how to work with them
- They are moving into backend engineering and are new to Git workflows, CI, FastAPI, Postgres and Docker.
- Explain every concept in plain, everyday language before using its terminology. Avoid unexplained jargon.
- The goal is learning by doing:
  - Before each step, explain the concept briefly with a simple example.
  - The user writes the core logic: regex checks, entropy, git log parsing, report.
  - Claude writes tests first, gives hints, reviews code, and handles boilerplate (config files, CI yaml, Docker).
  - Don't hand over finished core code unless the user asks.
- Go one small step at a time. Each step ends with tests passing and a commit.

## Rules
- Never use realistic-looking secrets in code or tests. Build fake ones at runtime (e.g. "AKIA" + "FAKE" + "0" * 12).
- Never print, log or store a raw secret. Use the redacted version and the HMAC fingerprint only.
- Git: Claude may commit locally, but asks the user for the commit message first and never pushes. The user pushes manually.
- Before committing, check the changes for real credentials or keys.

## Progress
- [x] Design doc v0.2 (plain language)
- [ ] Weekend 1, Saturday Step 1: Git basics, GitHub repo, project setup  ← NEXT
