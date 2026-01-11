# 《小说佳》AI能力对接与提示词规范（Draft）

## 1. 能力清单与输入输出
### 1.1 AI润色（FR-006）
- **输入**：
  - `text`：选中文本或章节全文
  - `styleHints`（可选）：文风、叙述人称、禁用词等
  - `constraints`（可选）：不改变剧情、不新增设定等
- **输出**：
  - `polishedText`
  - `notes`（可选）：做了哪些类型的改动（用词、句式、节奏）

### 1.2 回溯摘要（FR-007）
- **输入**：上一章（或N章）正文
- **输出**：
  - `summary`（200~500字可配置）
  - `characters`（可选）：人物与关系
  - `openLoops`（可选）：未解决悬念

### 1.3 下一章节预告（FR-009）
- **输入**：
  - 当前章节正文
  - 可选：前N章摘要、人物设定、全书主线
- **输出**：
  - `previewText`：下一章预告/方向指引
  - `beats`（可选）：要点列表（可作为大纲）

### 1.4 智能体全书优化（FR-012~FR-014）
- **输入**：
  - 全书章节内容（按章节分块）
  - 目标：风格统一/一致性修复/节奏优化
  - 约束：不得改变关键剧情、不得替换专有名词等
- **输出**（强制）：
  - `changeList`：改动记录清单（见第3节）
  - `globalNotes`（可选）：发现的问题与建议

## 2. 提示词模板（建议内置）
> 模板应支持变量：`{{chapterTitle}}`、`{{chapterText}}`、`{{selectedText}}`、`{{previousSummaries}}` 等。

### 2.1 润色模板（示例）
- 目标：提升流畅度与表达，不改变剧情与信息量
- 约束：
  - 不新增设定/人物
  - 不改变时间顺序
  - 保持原人称与叙述视角

### 2.2 预告模板（示例）
- 输出结构建议：
  - 1段“推进与冲突”
  - 1段“人物动机与选择”
  - 1句“悬念钩子”

### 2.3 智能体一致性修复模板（示例）
- 先找矛盾点与证据（引用章节位置）
- 再给出最小改动方案
- 最终只用 `changeList` 输出具体可应用改动

## 3. 改动记录清单（changeList）结构（强制）
### 3.1 数据结构（JSON概念）
- `changeList[]` 每项包含：
  - `id`：唯一ID
  - `chapterId` / `chapterIndex` / `chapterTitle`
  - `kind`：`replace` | `insert_before` | `insert_after` | `delete`
  - `locator`：定位信息（至少一种）
    - `paragraphIndex`（推荐）
    - 或 `beforeAnchor`/`afterAnchor`（用于无法稳定索引时）
    - 可选：`charRange`（若编辑器能提供稳定范围）
  - `beforeText`：原内容（delete/replace必填）
  - `afterText`：新内容（insert/replace必填）
  - `reason`：一句话原因
  - `risk`（可选）：低/中/高（高风险改动默认不勾选应用）

### 3.2 应用策略（避免误改）
- 默认采用“锚点匹配”或“段落索引”定位
- 应用前校验：
  - `beforeText` 与目标位置内容相似度/完全匹配（策略实现可选）
  - 不匹配则标记为“冲突”，需要人工处理，不得强行写入

### 3.3 展示策略
- 列表视图：章节、位置、原因、改动类型
- 对比视图：Before/After 并排
- 操作：逐条应用/跳过、全部应用、全部撤销

## 4. 提供方抽象（DeepSeek/智谱）
- 统一抽象：
  - `Provider`：deepseek | zhipu | ...
  - `Model`：字符串
  - `call(options)`：输入messages、temperature、maxTokens、stream等
- 错误分类（用于UI提示）：
  - `AUTH`（密钥错误/未配置）
  - `RATE_LIMIT`
  - `NETWORK`
  - `CONTENT_POLICY`（如供应商拦截）
  - `UNKNOWN`

## 5. 本地安全（与存储规范联动）
- API Key 不进入项目导出包
- 需要“导出时剥离敏感信息”的强约束

