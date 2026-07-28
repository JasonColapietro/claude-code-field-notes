# Claude Code Field Notes: Running AI Coding Agents in Production

**Six lessons from operating 20+ live software surfaces with Claude Code, by [Jason Colapietro](https://suedeai.ai/founder), Founder and CEO of [Suede Labs AI](https://suedeai.ai).**

Most writing about AI coding agents covers the first hour: install the CLI, write a prompt, watch it
edit a file. This covers what happens at month six, when agents run concurrently against real
production surfaces and the failure modes stop being about prompting.

These are abridged notes from *The Complete Claude Code Compendium*, a 110,000-word operator's
manual. Every figure below came off a command that was run or a file that was read.

---

## 1. A clean build is a compile check, not proof

A wallet-connect refactor passed build, type-check, and lint. It merged and deployed under standing
autonomy. Then it broke a live button on six marketing pages with a client-side exception the
instant anyone clicked it.

Nothing in the pipeline was wrong. The pipeline answers "does this compile and typecheck," and the
question that mattered was "does the button still work." Those are different questions and only one
of them was being asked.

The rule that came out of it: **verify the artifact you shipped, by doing the thing a user does.**
For an interactive change that means clicking it on the live domain, in a clean browser context,
after the deploy lands. It cost ten minutes to catch and revert. It would have cost nothing to
prevent.

Two corollaries worth adopting:

- **Verify the committed state, not your working tree.** A passing test against uncommitted local
  files proves nothing about what you pushed.
- **Verify against the live URL, not the build log.** A green deploy and a working page are
  different claims.

## 2. An empty environment variable is worse than a missing one

A production outage traced back to environment variables resolving as empty strings rather than
being absent. The code read them, found empty values, and took a silent fallback path: from a
durable Postgres store to an ephemeral local one, inside a serverless function, with no error
raised anywhere.

A missing variable crashes at boot and you find out in thirty seconds. An empty one is valid input.
The system keeps running and quietly does the wrong thing.

**Assert your configuration at startup, and make the assertion fail loudly.** Then verify the
datastore's identity from production itself rather than from your intent. If your config says
Postgres, ask production what it is actually writing to.

## 3. Money-path defaults must fail closed

A settlement toggle shipped opt-in, defaulting to false. Production was missing the column entirely,
so every priced endpoint mapped to dry-run, and dry-run skipped the payment challenge. The result:
every paid endpoint was free to call, while the billing system reported itself live.

The fix inverted the default. Missing or null now means charge; only an explicit toggle disables it.

The generalization applies past payments to any control whose failure is expensive: **when a default
must be wrong in one direction, choose the direction that fails safe.** For revenue, absence should
mean charge. For access, absence should mean deny.

## 4. Deploy conventions are attack surface

On some platforms, every file in a specific directory becomes a public HTTP route. Filename maps to
URL, with no other gate. That convention is convenient until a colocated test file lands there.

A file named `something.test.js` in that directory is not a test. It is an unauthenticated endpoint
that executes a test suite inside a production function when anyone requests it, boots whatever
servers the test defines, and holds the invocation open toward the platform's timeout ceiling.
Anyone who finds it can loop it.

The audit is one line per candidate file, and it checks production rather than your file tree:

```bash
curl -s -o /dev/null -w '%{http_code}' https://<domain>/api/<basename>
```

Anything that is not a real endpoint should answer 404. **Treat every file under a route-mapped
directory as a public URL, and confirm it against the deployed site rather than the repository.**
Framework conventions differ, so learn which of yours maps filenames to routes.

## 5. A registry reports what it was told; a process table reports what is

During a cleanup of finished agent workspaces, the session registry reported several as not running.
They had live processes inside them with child processes actively writing files. Acting on the
registry would have deleted a running agent's workspace mid-edit.

The check that works asks the operating system, not the bookkeeping:

```bash
lsof -d cwd 2>/dev/null | grep "<path>"
```

Two things make this worse than it sounds. **Workspaces go live while you audit them**, so a
directory that was idle ten minutes ago is not evidence about now; re-check immediately before
deleting. And **squash-merged branches look unmerged**: commit ancestry shows work ahead of main
even when the content already landed, because main moved on. Use `git cherry` or match commit
subjects rather than trusting ancestry, or you will keep dead workspaces and, worse, convince
yourself that merged work was lost.

## 6. When documentation is silent, measure

Documentation for agent tooling ages faster than it is written. Rather than guessing at a payload
shape, capture one. A hook that dumps its input to disk answers the question in a minute, for the
exact version you are running:

```bash
#!/bin/bash
payload=$(cat)
printf '%s\n' "$payload" >> /tmp/probe/events.jsonl
exit 0
```

Point every event you care about at that script, run one throwaway session, and read the log. Doing
this surfaced a documented event whose handler-type table omitted it, even though a handler on that
event demonstrably fires. **The installed binary is the source of truth. Documentation is a
secondary source, and version-gated features make it a moving one.**

---

## The pattern underneath

Every lesson here is the same shape. A system reported success while doing something else: a green
build, an empty variable, a billing toggle, a file tree, a session registry, a documentation page.
In each case the fix was to ask the thing itself instead of asking a record of it.

That gets more expensive to ignore as you add agents. One person reviewing one change can hold the
gap between "reported" and "actual" in their head. Six concurrent agents shipping against twenty
surfaces cannot, so the verification has to be mechanical, and it has to run against production.

## About the author

**Jason Colapietro** is the Founder and CEO of [Suede Labs AI](https://suedeai.ai), where he builds
creator-ownership infrastructure, programmable IP, and proof-of-creation systems for the AI era. He
operates the company's full production estate solo, more than twenty live surfaces, using AI coding
agents as the labor.

He is a published author and Forbes contributor, and he publishes an open-source
[skill pack](https://github.com/JasonColapietro/suede-creator-skills) for Claude Code.

- Web: [suedeai.ai](https://suedeai.ai) · Founder page: [suedeai.ai/founder](https://suedeai.ai/founder)
- GitHub: [@JasonColapietro](https://github.com/JasonColapietro)
- X: [@johnnysuede](https://x.com/johnnysuede)
- LinkedIn: [jasoncolapietro](https://www.linkedin.com/in/jasoncolapietro)
- Substack: [jasoncolapietro.substack.com](https://jasoncolapietro.substack.com)

## The full manual

*The Complete Claude Code Compendium* runs 110,055 words across 8 parts, 37 chapters, and 6
appendices, published by Johnny Suede Press. The reference half documents the Claude Code feature
surface (CLI, sessions, context and compaction, models and reasoning effort, CLAUDE.md and the
memory hierarchy, slash commands, agent skills, subagents, agent teams, hooks, MCP, plugins,
permissions, sandboxing, checkpoints, headless operation) verified against a live install rather
than against documentation. The operating half covers running a multi-surface estate: worktree
discipline, concurrent agent sessions, a dated incident log, deploy and spend discipline, and
operating cadence.

Not currently public. For access or licensing, reach out through [suedeai.ai](https://suedeai.ai).

---

<sub>Topics: Claude Code · AI coding agents · agentic engineering · LLM developer tooling ·
CLAUDE.md · agent skills · subagents · hooks · Model Context Protocol · git worktrees ·
production AI operations · DevOps for AI agents · solo founder engineering</sub>
