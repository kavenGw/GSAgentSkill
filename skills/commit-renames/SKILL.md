---
name: commit-renames
description: 从混合 Git 改动中拆出纯文件路径改名提交，保留内容改动和原有暂存状态。用于“先 commit 文件改名，方便 review”；不用于类型重命名重构或直接提交整个模块。
---

# Commit Renames

将 HEAD 中的原文件内容和文件模式原样放到新路径，形成独立提交；类型名、调用点和逻辑修改留待后续 review。Git 不存储“改名操作”，以相同 blob 和 mode 的路径映射证明纯改名。

## 确定范围

- 遵循目标仓库的提交约定，读取完整 `git status --porcelain=v1`、原生 `git diff` 与 `git diff --cached`。新文件单独读取；不能只凭 Git 的相似度推断映射。
- 根据差异、文件内容及 Unity `.meta` GUID 核对旧→新路径，生成 UTF-8 JSON 数组，例如 `[["src/Old.cs", "src/New.cs"]]`。路径相对于仓库根，使用 `/`。
- Unity 资源将配套 `.meta` 一同改名，保留原 GUID；脚本会自动补充存在于 HEAD 的配套 `.meta`。先检查改名对象是否有 MonoBehaviour、ScriptableObject 或路径加载约束；纯路径提交暂时使用旧类型名，不能将其宣称为可运行的完整重构。
- 用户已明确要求纯文件改名提交时直接执行。只有“改名部分”是否包含类型和调用点等内容确实不清楚时，才说明具体差异并询问边界。技能本身不增加确认门槛；只读请求不能变成提交授权。

## 准备并检查

使用 [scripts/rename_commit.py](scripts/rename_commit.py)，只依赖 Python 标准库和本地 Git：

```text
python -X utf8 <skill>/scripts/rename_commit.py prepare --repo <repo> --pairs <pairs.json>
```

脚本用临时 `GIT_INDEX_FILE` 从 HEAD 构造候选树，输出完整原生差异及状态文件路径，不改变真实索引、工作区或 HEAD。检查映射与请求一致，只有预期路径变化，内容行增删均为零。

脚本处理**已经暂存的改名**：旧路径已从真实索引移除，新路径已进入索引；新文件可以混有内容修改，也支持新文件暂存后继续编辑。该前置条件让提交后真实索引保持原样就能完整保留剩余改动。若改名尚未暂存，先解释当前状态及需调整的暂存范围；不通过整文件 `git add` 静默改变部分暂存意图。

遇到冲突、正在进行的 merge/rebase/cherry-pick、旧路径仍存在、新路径冲突、路径交换或脚本拒绝的文件类型，停止自动流程并报告具体原因。不要为了让脚本通过而 reset、stash、恢复文件或扩大提交范围。大小写改名在大小写不敏感文件系统上不由此脚本处理。

## 提交并验证

确认当前任务已有提交授权，并已看过候选差异，再将符合仓库约定的 message 写入临时 UTF-8 文件：

```text
python -X utf8 <skill>/scripts/rename_commit.py commit --state <state.json> --message-file <message.txt>
```

脚本检查准备后的 HEAD、分支、暂存内容及工作区快照未变，再使用隔离索引执行普通 `git commit -F`，保留 hooks。不要改用 `git commit -- <paths>`：它会采纳工作区内容，混入待拆分的代码修改。

完成条件：提交的父提交与候选基线一致，提交树精确等于已检查的候选树，真实索引条目和工作区改动快照保持不变。通常所有配对显示 `R100`；多个文件 blob 完全相同时 Git 可能展示不同配对，以完整树的路径/blob/mode 核验为准。二进制文件的 numstat 为 `-/-`，通过 blob 相同证明内容未变。

若提交失败或事后核验失败，先核对 HEAD 和错误输出；hooks 可能已经产生副作用或提交已经成功。脚本保留临时状态以便调查，不自动重试、重置历史或关闭 hooks。快照用于检测变化，不提供回滚。

成功后脚本删除自身临时索引和状态文件；清理本次创建的 pairs/message 临时文件。放弃未提交的候选时可运行 `discard --state <state.json>`，仅删除该候选的临时文件。

交付提交 hash、改名数量、零内容变更的核验结果，以及剩余暂存/工作区状态。是否编译按仓库要求说明；不自动 push。
