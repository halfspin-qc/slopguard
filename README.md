# slopguard

**Catches AI-hallucinated packages before you — or your CI — install them.**

AI coding assistants sometimes suggest packages that don't exist. Roughly 1
in 5 AI-generated code samples references a package that isn't real — and
attackers know this. They register the exact hallucinated names as real,
malicious packages and wait for someone to `pip install` or `npm install`
what their AI told them to. This is called **slopsquatting**.

slopguard checks every dependency declared in your project against the real
registry (PyPI, npm) and fails loudly if any of them don't actually exist.

```
$ slopguard .
slopguard — scanning /your/project
Found 11 declared dependencies. Checking against npm + PyPI...

⚠ 2 package(s) NOT FOUND on their registry:
  ✗ pandas-ai-turbo-autoclean [pypi] — declared in requirements.txt
      no PyPI project with this exact name
  ✗ react-auto-agent-orchestrator-pro [npm] — declared in frontend/package.json
      no npm package with this exact name

slopguard found 2 suspicious package(s). Failing.
```

## Install

```
pip install slopguard
```

## Use it directly

```
slopguard .                 # scan the current directory
slopguard /path/to/project  # scan anything else
slopguard . --quiet         # only print problems, skip the OK list
```

Exit code is `1` if anything's missing, `0` if everything's clean — built to
gate a CI pipeline, not just print a warning nobody reads.

## Add it to your CI (GitHub Actions)

Drop `.github/workflows/slopguard.yml` (included in this repo) into your own
project. Every pull request gets checked automatically.

## Add it as a pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/YOUR_USERNAME/slopguard
    rev: v0.1.0
    hooks:
      - id: slopguard
```

## What it checks

- `requirements.txt`
- `pyproject.toml` (PEP 621 and Poetry-style dependencies)
- `package.json` (`dependencies`, `devDependencies`, `peerDependencies`)

It checks what's **declared**, not raw `import` statements — that's
deliberate. Import names and package names often differ (`import yaml`
installs as `PyYAML`), which would create false positives. The real risk
shows up the moment a hallucinated name lands in a manifest file, which is
exactly what this checks.

## What it doesn't do (yet)

- Doesn't check Rust/crates.io or Go modules — PRs welcome
- Doesn't flag typosquats of *real* packages (e.g. `reqeusts`) — different
  problem, possibly a v2
- Doesn't scan git diffs only — currently a full-project scan every time

## Why this exists

Vibe coding crossed from trend to infrastructure in 2026, and the AI tools
writing your code don't always know which packages are real. slopguard is
the smallest possible check that closes the gap between "the AI said to
install this" and "this is actually safe to run."

MIT licensed.
