# 小说佳（本地小说创作软件）

**定位**：以“降低创作门槛、提升创作效率”为核心，打造“AI辅助 + 作者主导”的本地小说创作工具；集成 DeepSeek、智谱等API实现润色、回溯、下一章预告与全书智能体优化，并确保修改可追溯、可核对、可回滚。

## 文档
- **需求说明（PRD/SRS）**：`docs/requirements.md`
- **界面与交互（UI/UX Spec）**：`docs/ui-interactions.md`
- **本地存储与导入导出规范**：`docs/storage-format.md`
- **AI能力与改动清单规范**：`docs/ai-spec.md`

## 范围（核心）
- **开始创作**：左侧章节目录管理 + 右侧编辑器（AI润色/回溯阅读/提交保存）
- **提交后自动生成**：下一章节预告（可编辑保存）
- **智能体模式**：全章节统筹优化 + 输出“改动记录清单”（逐条应用/撤销）

## 本地运行（开发版）
> 当前仓库提供 **Python + Qt（PySide6）** 的本地桌面应用实现（MVP持续完善中）。

```bash
pip3 install -r requirements.txt
python3 -m novelja
```

### Linux 可能需要的系统依赖
如果启动时报 Qt/EGL 相关动态库缺失，可安装：

```bash
sudo apt-get update && sudo apt-get install -y libegl1
```

