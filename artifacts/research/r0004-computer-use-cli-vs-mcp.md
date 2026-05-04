---
created: 2026-05-03
id: r0004
kind: research
name: computer-use-cli-vs-mcp
status: draft
---

## Question

Which integration pattern should agents use to interact with external tools and services: **Computer Use / CLI** (shell execution) or **MCP** (Model Context Protocol)?

---

## Conclusion (Lead)

**Confirmed:** CLI wins on token efficiency, speed, composability, and reliability for tools the model was trained on. MCP wins on security, structured output, enterprise governance, and integrating remote/proprietary services.

**Recommendation:** Hybrid. Use CLI as the default for local dev workflows; adopt MCP for remote services, OAuth-gated APIs, and multi-tenant/compliance-sensitive contexts.

---

## Approach A — Computer Use / CLI (Shell Execution)

The agent invokes shell commands directly (bash, gh, git, docker, etc.) using a Bash tool or similar.

### Pros
| # | Factor | Detail |
|---|--------|--------|
| 1 | **Token efficiency** | No schema bloat. 4–32× cheaper per operation than MCP. At 10k ops/month: ~$3 (CLI) vs ~$55 (MCP). |
| 2 | **Training data** | Models trained on billions of terminal interactions. Well-known CLIs (git, gh, npm, docker) work with zero guidance. |
| 3 | **Composability** | Unix pipes: . MCP has no equivalent. |
| 4 | **Reliability** | 100% tool adherence vs 0.33 for MCP on complex tasks (Arize eval on GitHub tasks). |
| 5 | **Debuggability** | Output is visible, human-readable, easy to trace. |
| 6 | **Zero setup** | Tools already installed; no server config. |

### Cons
| # | Factor | Detail |
|---|--------|--------|
| 1 | **Unstructured output** | Agent must parse text. Fragile to formatting changes. |
| 2 | **Broad attack surface** | Shell access is wide; a compromised or misconfigured agent can run arbitrary commands. |
| 3 | **No type safety** | No schema; agent infers argument structure from training data or docs. |
| 4 | **Proprietary CLIs** | Company-internal CLIs have no training data. Agent needs explicit guidance (skills/docs). |

### Risks
- **Destructive commands**: , HEAD is now at 8332c17 docs(t0078): update adding-a-kind guide for folder form and ARTIFACT.md contract,  are one misfire away.
- **Credential exposure**: Full shell access means the agent can read , SSH keys, tokens in env vars.
- **Prompt injection via output**: Malicious content in command output can hijack agent behaviour.
- **No audit trail**: Shell invocations don't log to a centralised authority by default.

---

## Approach B — MCP (Model Context Protocol)

The agent calls structured tools exposed by an MCP server over JSON-RPC. Each server declares its tools via a schema.

### Pros
| # | Factor | Detail |
|---|--------|--------|
| 1 | **Structured output** | JSON responses with typed fields. No parsing ambiguity. |
| 2 | **Security & scoping** | Each server exposes only the capabilities it declares. Permissions are per-server. |
| 3 | **Discoverability** |  endpoint lets agents dynamically find available capabilities. |
| 4 | **Enterprise / OAuth** | OAuth flows, admin oversight, audit logging, multi-tenant SaaS — MCP is designed for this. |
| 5 | **Standardisation** | Open protocol: same server works with Claude, Gemini, Cursor, etc. |
| 6 | **Encapsulation** | Complex agents or services can be hidden behind a clean tool interface. |

### Cons
| # | Factor | Detail |
|---|--------|--------|
| 1 | **Token overhead** | Full tool schemas injected at session start. 150k+ tokens for enterprise setups. |
| 2 | **Setup cost** | Requires a running MCP server. Infrastructure to deploy and maintain. |
| 3 | **Ecosystem immaturity** | Post-2024 ecosystem; many servers are low-quality or incomplete. |
| 4 | **Opacity** | Tool executions are opaque; harder to debug than reading a bash command. |
| 5 | **Composability absent** | No native way to pipe MCP tool outputs together. |

### Risks
- **Schema injection attacks**: MCP server descriptions can embed instructions that manipulate the agent (tool poisoning).
- **Server availability**: Agent is blocked if the MCP server is down or misconfigured.
- **Token explosion**: Loading many MCP servers simultaneously can blow the context window, degrading all reasoning.
- **False trust**: Scoped permissions can give a false sense of security; server-side logic still needs to be hardened.
- **OAuth token management**: If auth tokens are mis-scoped or long-lived, a compromised MCP server exposes that service.

---

## Head-to-Head (Arize Eval — GitHub Tasks, n=25)

| Metric | CLI / Skills | MCP |
|--------|-------------|-----|
| Correctness | 0.826–0.834 | 0.826–0.834 |
| Tool adherence | >0.99 | 0.33 |
| Cost (complex tasks) | 1× | ~6× |
| Speed (complex tasks) | 1× | ~5× slower |
| Tool calls / task | ~5 | ~12 |

Correctness is nearly identical; efficiency strongly favours CLI.

---

## Decision Guide

| Situation | Recommended |
|-----------|-------------|
| Git, file ops, npm, docker, AWS CLI | CLI |
| Proprietary internal CLI (well-documented) | CLI + skill |
| Proprietary internal CLI (undocumented) | MCP (or document first) |
| Remote SaaS API (Notion, Figma, Jira) | MCP |
| Multi-tenant / OAuth-gated service | MCP |
| Compliance / audit trail required | MCP |
| Speed / token budget critical | CLI |

---

## Sources

- [CLI vs. MCP: Prioritizing OS-Level Portability for AI Agent Tools](https://earezki.com/ai-news/2026-05-01-why-cli-over-mcp/)
- [MCP vs CLI Skills for Agents — Arize AI eval](https://arize.com/blog/mcp-vs-cli-skills-for-agents-what-our-eval-found-and-which-you-should-use/)
- [CLIs or MCP for Coding Agents? Practical Comparison — DeployHQ](https://www.deployhq.com/blog/clis-or-mcp-for-coding-agents-practical-comparison)
- [On CLIs vs. MCP — HuggingFace Blog](https://huggingface.co/blog/nielsr/mcp-vs-cli)
- [CLI Tools vs MCP: Better AI Agents With Less Context](https://jannikreinhard.com/2026/02/22/why-cli-tools-are-beating-mcp-for-ai-agents/)
- [MCP vs CLI for AI Agents — Firecrawl](https://www.firecrawl.dev/blog/mcp-vs-cli)
- [The MCP vs. CLI Debate Is the Wrong Fight — Medium](https://medium.com/@tobias_pfuetze/the-mcp-vs-cli-debate-is-the-wrong-fight-a87f1b4c8006)