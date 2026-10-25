# Agent 递归记忆管理系统 (ARMS)

> 面向 AI Agent 的三层递归记忆管理引擎  
> 模拟海马体→新皮层记忆巩固模型  
> 让 AI 在跨会话环境中形成持续、可追溯的自我记忆网络

## 安装

```bash
pip install agent-memory
```

## 快速开始

```bash
# 初始化记忆目录
agent-memory init

# 加载种子记忆网（身份模板/项目注册表/索引框架）
agent-memory seed --load

# 记录今天的日记
agent-memory diary --append

# 查看今天的日记
agent-memory diary

# 执行记忆巩固（提取关键事件 → 更新长期记忆 → 更新索引）
agent-memory consolidate

# 搜索记忆
agent-memory search "关键词"

# 查看标签网络
agent-memory tags
```

## 架构

```
三层记忆架构：
  短期: memory/YYYY-MM-DD.md    ← 每日原始记录
  长期: MEMORY.md               ← 核心记忆/里程碑
  专题: memory/*.md             ← 按主题组织

夜间巩固（海马体→新皮层模型）：
  diary → extract_key_events() → merge_to_longterm() → update_index()
```

## 模块

| 模块 | 功能 |
|------|------|
| `store.py` | 三层记忆存储（日记/长期/专题） |
| `consolidator.py` | 记忆巩固引擎（规则提取+合并） |
| `index.py` | 标签索引网络（标签→文件→事件） |
| `reflex.py` | 快系统反射引擎（条件触发规则） |
| `seed.py` | 种子记忆网加载器 |

## 许可证

专有软件 · 著作权人：曹修达 © 2026
