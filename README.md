# GSAgentSkill

[中文](README_CN.md)

A collection of independent agent skills:

- **diagram-advisor** decides **which diagram to draw** before drawing it. It analyzes the question, recommends 2–4 candidate types with trade-offs, waits for your choice, then hands off to [drawio-skill](https://github.com/Agents365-ai/drawio-skill) to produce an editable `.drawio` file.
- **deepen-prompt** rethinks the current task from its goals and constraints, confirms trade-offs, and hands a grounded brief to a fresh agent for execution and independent verification. Invoke it explicitly; it is not selected automatically.
- **commit-renames** isolates file-path renames into a separate Git commit while preserving other staged content and working-tree changes. Includes a Python helper with Unity .meta support.

## Diagram requirements

- **[drawio-skill](https://github.com/Agents365-ai/drawio-skill)** — does the actual drawing. Install it first by following its README.
- **[draw.io desktop](https://www.drawio.com/)** — needed by drawio-skill for exports and some layout features.

Without drawio-skill, diagram-advisor still analyzes and recommends, then stops and asks where drawio-skill is installed.

## Install

Claude Code plugin (installs drawio-skill automatically, pinned to a tested version):

```
/plugin marketplace add kavenGw/GSAgentSkill
/plugin install gs-agent-skill@gs-agent-skill
```

The plugin exposes `gs-agent-skill:diagram-advisor`, `gs-agent-skill:deepen-prompt`, and `gs-agent-skill:commit-renames`. If any of these skills is already installed manually in `~/.claude/skills/` or a project's `.claude/skills/`, remove its old entry when switching to the plugin to avoid duplicate loading. Existing users of the old `diagram-advisor` marketplace should uninstall its plugins and remove that marketplace before installing this one.

npx:

```bash
npx skills add kavenGw/GSAgentSkill -g
```

Manual install (Claude Code):

```bash
git clone https://github.com/kavenGw/GSAgentSkill.git ~/src/GSAgentSkill
mkdir -p ~/.claude/skills
ln -s ~/src/GSAgentSkill/skills/diagram-advisor ~/.claude/skills/diagram-advisor
ln -s ~/src/GSAgentSkill/skills/deepen-prompt ~/.claude/skills/deepen-prompt
ln -s ~/src/GSAgentSkill/skills/commit-renames ~/.claude/skills/commit-renames
```

On Windows (`ln -s` in Git Bash copies instead of linking), use a junction from `cmd`:

```bat
mklink /J "%USERPROFILE%\.claude\skills\diagram-advisor" "%USERPROFILE%\src\GSAgentSkill\skills\diagram-advisor"
mklink /J "%USERPROFILE%\.claude\skills\deepen-prompt" "%USERPROFILE%\src\GSAgentSkill\skills\deepen-prompt"
mklink /J "%USERPROFILE%\.claude\skills\commit-renames" "%USERPROFILE%\src\GSAgentSkill\skills\commit-renames"
```

For Codex, link each skill into `~/.agents/skills/` instead:

```bash
mkdir -p ~/.agents/skills
ln -s ~/src/GSAgentSkill/skills/diagram-advisor ~/.agents/skills/diagram-advisor
ln -s ~/src/GSAgentSkill/skills/deepen-prompt ~/.agents/skills/deepen-prompt
ln -s ~/src/GSAgentSkill/skills/commit-renames ~/.agents/skills/commit-renames
```

On Windows, use the junction commands above with `.agents` instead of `.claude`. Each `SKILL.md` must end up at `<skills root>/<skill name>/SKILL.md`.

## Usage

> Use diagram-advisor to help me explain how our login flow handles token refresh.

1. **Analyze** — the core question, audience, scope, key objects and relations; facts vs. assumptions.
2. **Recommend** — a short table of candidate diagram types, with one marked as recommended. The catalog in `references/diagram-types.md` covers 35 draw.io-friendly types, with rules for telling similar types apart and size limits that suggest splitting.
3. **Draw** — after you pick, it reads drawio-skill's `SKILL.md` and follows its drawing and validation workflow.

It replies in the language you use.

To deepen a task, invoke `/gs-agent-skill:deepen-prompt` in Claude Code when installed as a plugin, `/deepen-prompt` for a manual installation, or `$deepen-prompt` in Codex. Supply a task or use the current conversation. The skill follows the target workspace's rules and uses its scratchpad location; without one, it uses a task-specific temporary directory. A subagent-capable environment is needed for the fresh-agent hand-off; otherwise it produces a brief for a new session. No diagram dependency is required for this skill.

To isolate file renames, invoke `/gs-agent-skill:commit-renames` (Claude Code plugin), `/commit-renames` (manual install), or `$commit-renames` (Codex). Requires Python 3 and Git. The skill verifies path mappings and staged state, then commits using an isolated index; content edits remain for later review. It does not push automatically.

## Note on drawio-skill invocation

drawio-skill declares `disable-model-invocation: true`, so the model cannot call it through the Skill tool. diagram-advisor therefore locates and reads drawio-skill's `SKILL.md` directly at hand-off. This is intentional.

## Acknowledgments

The diagram catalog and selection rules draw on [SeeCode](https://github.com/Aryanutkarsh/SeeCode) (MIT).

## License

MIT
