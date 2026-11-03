# How it works

Each workflow markdown file has two parts:

- **Frontmatter** (YAML between `---` markers): Configures when the workflow runs, what permissions it has, and what write operations are allowed.
- **Markdown body**: Contains your natural language instructions that the AI agent follows.

Two of its security guardrails:

- **Read-only by default**: Workflows have read-only repository permissions unless you explicitly grant more.
- **Safe outputs**: Write operations (such as creating issues, adding comments, or opening pull requests) are only allowed through validated `safe-outputs` declared in the frontmatter.

Source: [GitHub Agentic Workflows, GitHub Docs](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/about-github-agentic-workflows#how-agentic-workflows-work)
