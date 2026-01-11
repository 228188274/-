# 《小说佳》本地存储与导入导出规范（Draft）

## 1. 目标
- **可移植**：项目文件夹可整体拷贝迁移
- **可追溯**：提交/智能体应用产生版本快照
- **可扩展**：未来增加角色/大纲/素材库不破坏旧数据

## 2. 推荐项目结构（文件夹方案）
> 也可用SQLite实现；本规范给出“文件夹+JSON”最小可行落盘。

```
<workspace>/<projectName>/
  project.json
  chapters/
    0001.md
    0002.md
    ...
  previews/
    0001_next.md        # “第1章提交后生成的下一章预告”
  versions/
    snapshots/
      <snapshotId>/
        project.json
        chapters/
          0001.md
          ...
    agent-runs/
      <agentRunId>.json  # 智能体运行记录+改动清单
  cache/
    summaries.json       # 回溯摘要缓存（可选）
```

## 3. `project.json`（概念字段）
- `id`：字符串（UUID）
- `title`：作品名
- `createdAt` / `updatedAt`
- `chapterOrder`：章节ID数组（保持顺序）
- `chapters`：章节元信息映射
  - `id`、`index`、`title`、`status`（draft/submitted）
  - `file`：对应 `chapters/0001.md`
  - `wordCount`、`lastModifiedAt`
  - `lastSubmittedAt`（可空）
  - `lastSnapshotId`（可空）
- `settings`（可选）
  - `autosave`：启用与间隔
  - `export`：导出偏好
  - `ai`：模型选择（不包含密钥）

## 4. 章节文件格式（最低要求）
- 默认使用 `UTF-8`
- 推荐使用 `Markdown`
  - 第一行可选：`# 第X章 标题`
  - 正文为Markdown或纯文本均可

## 5. 预告文件
- 与“已提交章节”绑定：`previews/<chapterIndex>_next.md`
- 允许为空（作者未填写）
- 允许多版本（可选）：如 `previews/0001_next.v2.md`

## 6. 导入规范（txt/md）
### 6.1 整本导入
- 输入：单文件（txt/md）
- 默认章节分隔规则（可配置）：
  - 正则：`^第[零一二三四五六七八九十百千0-9]+章.*$`（按行匹配）
  - 或Markdown标题：`^#\s+第.*章.*$`
- 未命中分隔规则：
  - 作为单章导入（“第1章”），并提示用户可在导入向导里设置分隔

### 6.2 单章导入
- 导入到当前选中章节
- 冲突策略（必须二选一并在UI明确）：
  - 覆盖
  - 追加（追加前插入分隔线）

## 7. 导出规范
### 7.1 导出整本
- 输出：一个文件（txt/md）或一个项目包（zip，推荐）
- 文件导出拼接规则：
  - 可选包含目录
  - 每章之间加入固定分隔（如两个空行 + `---`）

### 7.2 项目包导出（zip）
- 包含：章节、预告、版本快照、智能体改动清单
- **不得包含**：API密钥等敏感配置

## 8. 版本快照
- 触发：
  - 章节提交时（FR-008）
  - 智能体批量应用前（FR-015）
- 内容：
  - `project.json` 与全部 `chapters/*.md`（或范围内章节，需策略固定）
- 命名：
  - `snapshotId` 使用时间戳+随机串（短ID即可）

