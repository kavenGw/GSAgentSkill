# GSAgentSkill

[English](README.md)

一组保持独立入口的 Agent 技能：

- **diagram-advisor**：先分析你希望用图回答的问题，推荐 2～4 种候选图类型并说明取舍，等你选定后交给 [drawio-skill](https://github.com/Agents365-ai/drawio-skill)（[中文说明](https://github.com/Agents365-ai/drawio-skill/blob/main/README_CN.md)）生成可编辑的 `.drawio` 文件。
- **deepen-prompt**：从目标与硬约束重新思考当前任务，确认取舍，再把有证据支撑的任务书交给全新 agent 执行并独立核验。仅手动调用，不自动触发。
- **commit-renames**：从混合 Git 改动中拆出纯文件路径改名提交，保留其他暂存内容与工作区改动。附带 Python 脚本，支持 Unity 配套 .meta。

## 绘图依赖

- **[drawio-skill](https://github.com/Agents365-ai/drawio-skill)**：负责实际绘制，请先按其 [中文说明](https://github.com/Agents365-ai/drawio-skill/blob/main/README_CN.md) 安装。
- **[draw.io 桌面版](https://www.drawio.com/)**：drawio-skill 导出图片及部分布局功能需要。

未安装 drawio-skill 时，diagram-advisor 仍会完成分析和推荐，之后停下并询问 drawio-skill 的位置。

## 安装

Claude Code 插件（自动安装依赖 drawio-skill，固定在已验证版本）：

```
/plugin marketplace add kavenGw/GSAgentSkill
/plugin install gs-agent-skill@gs-agent-skill
```

插件安装后技能名为 `gs-agent-skill:diagram-advisor`、`gs-agent-skill:deepen-prompt` 和 `gs-agent-skill:commit-renames`。如果之前在 `~/.claude/skills/` 或项目 `.claude/skills/` 中手动安装了任一技能，切换到插件时请移除其旧入口，避免重复加载。旧 `diagram-advisor` marketplace 用户应先卸载其中的插件并移除旧 marketplace，再安装新版。

npx：

```bash
npx skills add kavenGw/GSAgentSkill -g
```

手动安装（Claude Code）：

```bash
git clone https://github.com/kavenGw/GSAgentSkill.git ~/src/GSAgentSkill
mkdir -p ~/.claude/skills
ln -s ~/src/GSAgentSkill/skills/diagram-advisor ~/.claude/skills/diagram-advisor
ln -s ~/src/GSAgentSkill/skills/deepen-prompt ~/.claude/skills/deepen-prompt
ln -s ~/src/GSAgentSkill/skills/commit-renames ~/.claude/skills/commit-renames
```

Windows 下 Git Bash 的 `ln -s` 默认是复制而非链接，请在 `cmd` 中创建 junction：

```bat
mklink /J "%USERPROFILE%\.claude\skills\diagram-advisor" "%USERPROFILE%\src\GSAgentSkill\skills\diagram-advisor"
mklink /J "%USERPROFILE%\.claude\skills\deepen-prompt" "%USERPROFILE%\src\GSAgentSkill\skills\deepen-prompt"
mklink /J "%USERPROFILE%\.claude\skills\commit-renames" "%USERPROFILE%\src\GSAgentSkill\skills\commit-renames"
```

Codex 将三个技能分别链接到 `~/.agents/skills/`：

```bash
mkdir -p ~/.agents/skills
ln -s ~/src/GSAgentSkill/skills/diagram-advisor ~/.agents/skills/diagram-advisor
ln -s ~/src/GSAgentSkill/skills/deepen-prompt ~/.agents/skills/deepen-prompt
ln -s ~/src/GSAgentSkill/skills/commit-renames ~/.agents/skills/commit-renames
```

Windows 使用上面的 junction 命令，将 `.claude` 换成 `.agents`。最终 `SKILL.md` 须位于 `<技能根目录>/<技能名>/SKILL.md`。

## 使用

> 用 diagram-advisor 帮我梳理登录流程里 token 刷新是怎么处理的。

1. **分析**：核心问题、读者、范围、关键对象与关系，区分事实与假设。
2. **推荐**：以表格列出候选图类型，标出推荐项。`references/diagram-types.md` 收录 35 种适合 draw.io 的图类型，含相近类型的判别规则和提示拆图的规模上限。
3. **绘制**：你选定后，读取 drawio-skill 的 `SKILL.md`，按其绘制与校验流程执行。

回复语言跟随你使用的语言。

深化任务时，Claude Code 插件安装使用 `/gs-agent-skill:deepen-prompt`，手动安装使用 `/deepen-prompt`，Codex 使用 `$deepen-prompt`。可以附带题目，也可以沿用当前对话。该技能遵循目标工作区规则，临时材料使用工作区约定的 scratchpad；没有约定时使用独立的系统临时目录。全新 agent 交接需要环境支持子 agent，否则生成任务书交给新会话执行。此技能不依赖绘图工具。

拆分纯文件改名提交时，使用 `/gs-agent-skill:commit-renames`（Claude Code 插件）、`/commit-renames`（手动安装）或 `$commit-renames`（Codex）。需要 Python 3 和 Git。先核对旧→新路径及暂存状态，再用隔离索引提交；内容修改保留待后续审阅，不自动推送。

## 关于 drawio-skill 的调用方式

drawio-skill 声明了 `disable-model-invocation: true`，模型无法通过 Skill 工具调用它。因此 diagram-advisor 在交接时直接定位并读取其 `SKILL.md`，这是有意设计。

## 致谢

图类型目录和选型规则参考了 [SeeCode](https://github.com/Aryanutkarsh/SeeCode)（MIT）。

## 许可证

MIT
