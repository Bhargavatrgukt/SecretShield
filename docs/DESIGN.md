# SecretShield: Design Document

**Catch passwords and keys before they leak.**

| | |
|---|---|
| Status | Draft v0.2 |
| Last updated | 14 Nov 2026 |
| Author | Personal portfolio project |

> **How to read this doc:** whenever a new technology or term shows up, there's a short **💡 What is this?** box
> explaining it in everyday language. You don't need to know anything in advance.

---

## 1. The problem

Developers sometimes put secret values straight into their code by accident. For example:

```python
DATABASE_PASSWORD = "SuperSecret123"
```

Then they commit and push the code. Even if they delete that line the next day, **the password is still in the
project's history**, and anyone who can see the project can go back and find it.

> **💡 What is Git history?**
> Git is like a "save game" system for code. Every time you commit, Git takes a snapshot and keeps it forever.
> Deleting a line in today's snapshot doesn't erase it from yesterday's. That's why leaked secrets are dangerous:
> they hide in old snapshots.

Real-world examples of secrets that leak this way:
- Cloud keys (AWS, Google Cloud), which can be used to run up huge bills
- Database passwords
- API tokens (like a password that lets one program talk to another service)
- Private keys (used for encryption and server login)

## 2. What SecretShield does

SecretShield looks through code, **including its full history**, and reports anything that looks like a secret.

It will grow over 4 stages:

| Stage | What you can do at the end | Technologies you learn |
|---|---|---|
| **1** | Run `python -m secretshield scan` in a folder and get a report of leaked secrets. GitHub automatically runs your tests on every push. | Python, Git, regex, pytest, GitHub, GitHub Actions |
| **2** | Send "please scan this repo" to a web service; results are saved in a database. | FastAPI, PostgreSQL |
| **3** | Start the whole thing on any computer with one command. | Docker, Docker Compose |
| **4** | When someone opens a pull request on GitHub, SecretShield scans it, comments on it, and blocks the merge if it finds secrets. | Webhooks, GitHub API |

Every stage ends with something **finished and working**. Stopping after any stage still leaves you with a real project.

### What we are NOT building (to keep it manageable)
- Checking whether a found key actually works
- Automatically cancelling or changing leaked keys
- A website/dashboard with pages and buttons
- Scanning images, PDFs, zip files or other non-text files

---

## 3. Stage 1: the scanner

This is the heart of the project. Everything after it is a different way of *using* the scanner.

### 3.1 How the scanner thinks

The scanner reads code **one line at a time** and asks two questions:

**Question 1: "Does this line match a known secret format?"**

Many secrets have a recognisable shape. AWS keys always start with `AKIA` followed by 16 capital letters/digits.
GitHub tokens always start with `ghp_`. Private keys always start with `-----BEGIN ... PRIVATE KEY-----`.

We describe these shapes using **regex**.

> **💡 What is regex?**
> Regex (regular expression) is a mini-language for describing text patterns.
> `AKIA[0-9A-Z]{16}` means: *the letters AKIA, then exactly 16 characters that are digits or capital letters.*
> It's like a search box that understands "any 16 capital letters" rather than only exact words.

**Question 2: "Is a secret-sounding name being given a random-looking value?"**

Not every secret has a known shape. Look at this:

```python
api_token = "a8fJ92kLmP7xQ3zN5vB4"
```

No pattern for that, but a human can tell it's a secret because:
1. The variable is called `api_token`, a suspicious name.
2. The value looks **random**, not like a normal word.

We measure "how random does this look?" with a score called **entropy**.

> **💡 What is entropy?**
> A number that says how mixed-up a piece of text is.
> `"aaaaaaaa"` → very low (same letter repeated).
> `"password"` → medium (a real word).
> `"a8fJ92kLmP7xQ3zN"` → high (looks like random keyboard mashing).
> Real passwords and tokens are usually high. We'll write the formula ourselves; it's about 10 lines of Python.

We only report it if **both** are true (a suspicious name *and* a random-looking value). Using either check alone gives
too many false alarms.

### 3.2 Avoiding false alarms

A scanner that cries wolf gets ignored. We skip lines like these on purpose:

| Line | Why it's fine |
|---|---|
| `password = os.environ["DB_PASSWORD"]` | Reads the secret from the environment. That's the *correct* way to handle secrets. |
| `api_key = "your-api-key-here"` | Obvious placeholder |
| `token = "xxxxxxxxxxxx"` | Placeholder |
| `secret = "abc123"  # secretshield:ignore` | Developer marked it as OK on purpose |

> **💡 What is an environment variable?**
> A value stored *outside* your code, in the computer or server settings. The code says "go fetch the value
> called DB_PASSWORD" instead of containing the password itself. This is how secrets should be handled.

### 3.3 Where the rules live

Patterns are stored in a separate settings file (`rules/default.yaml`), not mixed into the Python code.
Adding a new secret type means adding a few lines to that file, with no code changes.

> **💡 What is YAML?**
> A simple, human-readable format for settings files, built from indentation and `name: value` pairs.

```yaml
rules:
  - id: aws-access-key
    description: AWS access key
    pattern: 'AKIA[0-9A-Z]{16}'
    severity: CRITICAL

  - id: github-token
    description: GitHub personal access token
    pattern: 'ghp_[0-9A-Za-z]{36}'
    severity: CRITICAL

  - id: private-key
    description: Private key file contents
    pattern: '-----BEGIN [A-Z ]*PRIVATE KEY-----'
    severity: CRITICAL
```

**Severity** is how bad the leak is: `CRITICAL` → `HIGH` → `MEDIUM` → `LOW`.

### 3.4 Three things the scanner can scan

| Mode | Plain meaning | When it's useful |
|---|---|---|
| **Folder** | Look at the files as they are right now | Quick check before committing |
| **Recent commits** | Look only at what changed in the last few commits | Checking a pull request; fast |
| **Full history** | Look at every change ever made | Auditing a project for old, "deleted" leaks |

**How we read history:** Git can print every change ever made with the command `git log -p`. It shows each commit,
with added lines starting with `+` and removed lines starting with `-`.

```
commit 4f2a91c...
+++ b/config.py
+DATABASE_PASSWORD = "SuperSecret123"      ← added in this commit: SCAN IT
```

**The key idea:** every line that has ever existed in the project was *added* in some commit. So if we scan
every `+` line in `git log -p`, we've checked the entire history, and we know exactly **which commit**
introduced each secret. Reading this output in our own Python code (instead of using a ready-made library) is where
you'll really learn how Git works.

### 3.5 What a finding looks like

```
[CRITICAL] aws-access-key
  File:   config/settings.py
  Line:   24
  Commit: 4f2a91c
  Value:  AKIA**************** (20 characters)
```

### 3.6 Golden rule: never show the real secret

Our own tool must never become a leak. So:
- **On screen / in reports:** show only the first 4 characters, then stars (`AKIA************`).
- **To recognise the same secret again later:** store a **fingerprint** instead of the secret.

> **💡 What is a fingerprint (hash)?**
> A function that turns any text into a fixed-length scramble, like `9f86d081...`. The same input always gives the
> same scramble, but you **cannot reverse it** to get the original. So we can tell "this is the same secret we saw
> last week" without keeping the secret. We'll add a private key to the scramble (called HMAC) so nobody can guess
> short passwords by trying millions of options.

### 3.7 Exit codes: how the scanner says "pass" or "fail"

> **💡 What is an exit code?**
> When a program finishes, it hands back a number to whatever started it. `0` means "all good"; anything
> else means "something's wrong". Automated systems like GitHub Actions read this number to decide pass/fail.

| Exit code | Meaning |
|---|---|
| `0` | No serious secrets found ✅ |
| `1` | Secrets found ❌ |
| `2` | The scanner itself broke (e.g. folder isn't a Git repo) ❌, because "couldn't check" must never count as "safe" |

### 3.8 Testing

> **💡 What is pytest?**
> A Python tool for automated tests: small functions that check your code gives the right answer.
> Example: "if I scan a line containing an AWS key, I expect 1 finding". You run all tests with one command.

Situations we'll test:

| Situation | Expected result |
|---|---|
| AWS key in a file | Found, CRITICAL |
| Normal code with no secrets | Nothing found |
| Secret added in one commit, deleted in the next | **Still found** in full-history mode, with the original commit |
| Same secret twice in one file | Reported once |
| `password = os.environ["X"]` | Nothing found |
| `api_key = "your-api-key-here"` | Nothing found |
| Image or binary file | Skipped |
| Report output | Never contains the real secret |

⚠️ **Rule for test data:** we never write a realistic-looking secret directly in our code, even a fake one.
Tests build fake secrets while running (e.g. `"AKIA" + "FAKE" + "0" * 12`). Otherwise GitHub's own secret
protection, and our own scanner, would flag our test files.

### 3.9 GitHub + GitHub Actions

> **💡 What is GitHub?**
> A website that stores Git projects online so others (and recruiters!) can see them.

> **💡 What is CI / GitHub Actions?**
> CI ("continuous integration") means automatically checking code every time it changes.
> GitHub Actions is GitHub's built-in robot: you give it a small instruction file, and on every push it
> starts a fresh computer, installs your project, runs your tests, and shows ✅ or ❌ next to the commit.

In Stage 1, our GitHub Actions setup will:
1. Run all pytest tests.
2. Run **SecretShield on its own code** (a nice demo: the tool guards itself).

### 3.10 Folder layout for Stage 1

```
SecretShield/
├── secretshield/              ← our Python package (the actual code)
│   ├── __main__.py            ← lets you run: python -m secretshield scan
│   ├── rules.py               ← loads rules from the YAML file
│   ├── pattern_check.py       ← Question 1: regex
│   ├── entropy_check.py       ← Question 2: randomness
│   ├── filters.py             ← skips placeholders, env variables, ignore comments
│   ├── git_reader.py          ← reads files / commits / history
│   ├── redact.py              ← hides secrets + makes fingerprints
│   └── report.py              ← prints the report, picks exit code
├── rules/default.yaml
├── tests/
├── docs/DESIGN.md             ← this file
├── .github/workflows/ci.yml   ← GitHub Actions instructions
├── pyproject.toml             ← project info + dependencies
└── README.md
```

---

## 4. Stage 2: web service + database *(details written when we reach it)*

> **💡 What is an API / web service?**
> A program that waits for requests over the internet and replies. Instead of a person typing a command,
> another program sends: "scan this repo", and gets back: "scan #42 started".

> **💡 What is FastAPI?**
> A Python library for building web services quickly. You write normal Python functions; FastAPI makes them
> reachable over the web and auto-creates a test page in the browser.

> **💡 What is PostgreSQL?**
> A database: like a very powerful, very reliable set of spreadsheets that programs read and write.

What we'll add:
- **Endpoints** (web addresses the service answers):
  - `POST /scans`: start a scan of a GitHub repo
  - `GET /scans/{id}`: is it done? how many findings?
  - `GET /scans/{id}/findings`: list the findings
  - `GET /health`: is the service alive?
- **Two database tables:**
  - `scans`: one row per scan (which repo, when, status, how many findings)
  - `findings`: one row per secret found (file, line, commit, severity, hidden value, fingerprint). **Never the real secret.**

## 5. Stage 3: Docker *(details written when we reach it)*

> **💡 What is Docker?**
> "It works on my machine" is a classic problem. Docker packs your app *plus everything it needs*
> (the right Python version, libraries, settings) into a box called a **container**, which runs the
> same way on any computer.
> **Docker Compose** starts several containers together, here our app and the PostgreSQL database, with one command.

Goal: `docker compose up` → the whole system is running.

## 6. Stage 4: GitHub integration *(details written when we reach it)*

> **💡 What is a pull request (PR)?**
> On GitHub, you propose changes on a separate branch and open a "pull request" asking to merge them into
> the main code. It's where code review happens.

> **💡 What is a webhook?**
> A "call me when something happens" arrangement. We tell GitHub: *"whenever a pull request is opened,
> send a message to this web address."* GitHub does that, and our service wakes up and scans.

The flow:
```
Developer opens a pull request on GitHub
        │
        ▼
GitHub sends a webhook message to SecretShield
        │
        ▼
SecretShield checks the message is really from GitHub (shared secret)
        │
        ▼
Downloads the code → scans the new commits → saves results in database
        │
        ▼
Posts a comment on the pull request:  "⚠️ 1 secret found in config.py line 24"
        │
        ▼
Marks the PR check as ❌ so it can't be merged
```

Because our laptop isn't reachable from the internet, we'll use a free tunnel tool (like ngrok) during development
so GitHub can reach it.

---

## 7. Safety rules for the whole project

1. Never print, log, or save a real secret, only the hidden version and fingerprint.
2. Keep our own keys (GitHub token, fingerprint key, database password) in environment variables, never in code.
3. Never commit a `.env` file. Commit a `.env.example` with fake placeholder values instead.
4. Check that webhook messages really come from GitHub before acting on them.
5. When downloading someone's repo to scan, use a temporary folder, set a time limit, and delete it afterwards.

---

## 8. Schedule

About 12 hours per weekend. Each step ends with **tests passing + a commit**.

### Weekend 1: Stage 1 (scanner + GitHub + Actions)

**Saturday**
| # | Step | Time |
|---|---|---|
| 1 | Learn: Git basics (commit, branch, push), GitHub account + new repo, project setup | 2h |
| 2 | Learn: regex. Build: load rules from YAML, pattern check, with tests | 2.5h |
| 3 | Learn: entropy. Build: randomness check + false-alarm filters, with tests | 2h |

**Sunday**
| # | Step | Time |
|---|---|---|
| 4 | Build: scan a folder; hide secrets + fingerprints | 1.5h |
| 5 | Learn: how `git log -p` works. Build: recent-commits + full-history modes | 2.5h |
| 6 | Build: report + exit codes. Learn + set up GitHub Actions | 1.5h |
| 7 | README with example output | 0.5h |

✅ **Weekend 1 done when:** a test repo where a secret was added *and then deleted* gets flagged by full-history scan,
and GitHub shows a ✅ on your pushes.

### Weekend 2: Stage 2 (FastAPI + PostgreSQL)
### Weekend 3: Stage 3 (Docker) + start Stage 4
### Weekend 4: finish Stage 4 + polish README, record demo

(Weekday evenings, if you have them, can absorb overflow.)

---

## 9. Later ideas (after Stage 4)

- Run SecretShield automatically before every commit (a "pre-commit hook"), so secrets are caught *before* they're committed
- An "accepted findings" list so known false alarms stop showing up
- Show "this same secret appeared in 3 different repos" using fingerprints
- Output in SARIF format so GitHub shows findings in its Security tab
- Per-secret-type advice on how to cancel and replace the leaked key

---

## 10. Decisions made

| Question | Decision |
|---|---|
| Where is the code hosted? | GitHub (public repo, for the portfolio) |
| Which automation system? | GitHub Actions |
| Python version | 3.11 or newer |
| What counts as "fail"? | Any CRITICAL or HIGH finding. MEDIUM (randomness-only) findings are shown as warnings |
| Use a Git library or read `git` command output ourselves? | Read it ourselves, for the learning value |
