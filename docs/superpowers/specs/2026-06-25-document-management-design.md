# 简历/文档管理 + 上下文增强 - 设计文档

**日期**: 2026-06-25
**状态**: 待审核

## 一句话概述

新增一个管理页(`/manage`),上传简历(PDF)和面试题库(.md);面试生成建议时,把这些文档全文拼进 system prompt,让 GLM 引用真实经历、参考已准备的答案。放弃 RAG,直接用上下文增强。

## 背景与决策

### 为什么不用 RAG,直接塞上下文

经评估,简历 + 文档总量在**几万字**量级(约 6k~33k token),远小于 GLM-4-Plus 的 128k 上下文窗口。此量级下:

- **直接塞上下文更准**:信息无损,LLM 看到完整简历不会漏经历;RAG 检索可能漏关键片段
- **实现简单**:无需切分/向量化/向量库/检索链路
- **延迟低**:少一次检索调用
- **成本可接受**:面试是手动触发的低频场景,每次 +33k token 成本可忽略

RAG 适用于"海量文档(几百上千份)、单次塞不下"的场景,本项目未到该量级。

### 两类文档的定位

| 文档 | 格式 | 类型标记 | 在 prompt 里的作用 |
|------|------|---------|------------------|
| 简历 | PDF | `resume` | "回答时引用用户的真实经历,不要编造" |
| 面试题库 | Markdown(.md) | `qa` | "若面试官问题接近题库里的题,优先参考用户已准备的答案" |

面试题库内容:常见面试题及答案、用户假设面试官会问的问题及提前写好的答案。

## 核心交互流程

```
管理页 /manage
    │
    │  上传 PDF / .md(手动选类型: 简历 / 题库)
    ▼
后端解析出全文文本 → 存入内存 DocumentStore(全局单例)
    │
    │  面试页 / (无感升级)
    ▼
用户点"生成建议"
    │
    ▼
SuggestService.build_messages:
  system prompt + [简历全文] + [题库全文] + 历史轮次 + 当前问题
    │
    ▼
GLM 生成基于真实经历/题库的建议
```

## 整体架构

```
┌─────────────────────────────────────────────────────┐
│  浏览器 (React + React Router)                       │
│  /           面试助手页(现有,无感升级)              │
│  /manage     管理页(新)                              │
│    - 上传 PDF / .md(手动选类型)                      │
│    - 文档列表(名称/类型/大小/删除)                   │
└───────────────┬─────────────────────────────────────┘
                │ REST
┌───────────────▼─────────────────────────────────────┐
│  后端 (FastAPI)                                      │
│  routes/documents.py (新)                            │
│   - POST /api/documents/upload  接收 PDF/.md         │
│   - GET  /api/documents/list                         │
│   - DELETE /api/documents/{id}                       │
│  services/doc_parser.py (新)                         │
│   - PDF: pypdf 提取纯文本                             │
│   - MD: 直接读 UTF-8(保留 markdown 格式)            │
│  services/document_store.py (新)                     │
│   - 全局单例,内存存 {id,filename,doc_type,text,size} │
│  suggest / ask 链路升级:                             │
│   - build_messages 时把文档全文拼进 system prompt    │
│   - 简历和题库分开标注用途                            │
└─────────────────────────────────────────────────────┘
```

## 模块设计

### 新增目录结构

```
backend/app/
├── routes/
│   └── documents.py          # 新:文档上传/列表/删除
├── services/
│   ├── doc_parser.py         # 新:PDF/MD 解析
│   └── document_store.py     # 新:内存文档存储
├── schemas.py                # 改:新增 Document 相关模型
├── prompts.py                # 改:system prompt 追加文档占位
└── services/suggest.py       # 改:build_messages 拼入文档
```

```
frontend/src/
├── App.tsx                   # 改:引入 React Router
├── routes/                   # 新
│   ├── InterviewPage.tsx     # 新:现有 App 内容迁移
│   └── ManagePage.tsx        # 新:管理页
├── components/
│   ├── DocumentUpload.tsx    # 新:上传区
│   └── DocumentList.tsx      # 新:文档列表
├── hooks/
│   └── useDocuments.ts       # 新:文档 CRUD
└── api/
    └── documents.ts          # 新:文档 API 客户端
```

### 后端模块

#### `services/document_store.py`(内存,全局单例)

```python
class Document:
    id: str
    filename: str
    doc_type: str        # "resume" | "qa"
    text: str            # 解析后的全文
    size_bytes: int

class DocumentStore:
    _docs: dict[str, Document]

    def add(filename, doc_type, text, size_bytes) -> Document
    def list() -> list[Document]
    def delete(id) -> bool
    def get_by_type(doc_type) -> list[Document]
```

- 全局单例(同 SessionStore 风格),不挂在 InterviewSession 上
- 文档跨 session 共享:管理页上传后,任何面试会话都能用

#### `services/doc_parser.py`

```python
def parse_document(filename: str, file_bytes: bytes) -> str:
    """按扩展名分发解析,返回纯文本。"""
    # .pdf  -> pypdf 提取文本
    # .md   -> file_bytes.decode("utf-8"),保留 markdown 格式
    # 其它  -> raise ValueError("不支持的格式")
```

- PDF 用 `pypdf`(纯 Python、无系统依赖)
- Markdown 保留 `#`、`-`、代码块等符号,帮 LLM 理解文档结构
- 不做切分(全文塞上下文,无需切)

#### `routes/documents.py`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/documents/upload` | multipart 上传,字段:`file` + `doc_type`(resume/qa) |
| GET | `/api/documents/list` | 返回文档列表(不含 text 全文,只含元信息) |
| DELETE | `/api/documents/{id}` | 删除文档 |

**文件不落盘**——PDF/.md 解析出文本后只存文本到内存,原文件丢弃。

#### `prompts.py` 改动

system prompt 末尾追加文档拼接区(由 suggest 组装时填充):

```
[原 system prompt: 面试教练]

====== 用户的简历 ======
{resume_text}

====== 用户的面试题库(常见问题及准备好的答案)======
{qa_text}

使用说明:
- 简历:回答时引用用户的真实经历,不要编造
- 题库:如果面试官的问题接近题库里的题,优先参考用户已准备的答案
```

#### `services/suggest.py` 改动

`build_messages` 组装时:
1. 从 `DocumentStore` 取所有 `resume` 文档,拼接全文
2. 取所有 `qa` 文档,拼接全文
3. 拼进 system message(按上面的格式)
4. 无文档时,system prompt 退回原版(不追加空区,避免误导)

**追问链路(`/api/ask`)同步拼接**——保持建议和追问的上下文一致。

### 前端模块

#### 管理页视觉刷新

管理页沿用主面试页的清爽智能视觉体系，避免出现浏览器默认表单样式：

- 页面顶部使用 hero 卡片，包含“返回面试”、页面标题、用途说明和文档统计。
- 内容区左右两栏：左侧上传文档，右侧已上传文档列表。
- 上传区使用卡片式文件选择入口、胶囊式文档类型选择和高优先级上传按钮，底层仍保留原生 `input[type=file]` 以保证兼容性。
- 文档列表使用卡片行展示文件名、类型、大小和删除按钮；空列表时显示友好的空状态提示。
- 本次刷新只调整前端表现层，不改变接口、文档存储、上传或删除的数据流。

#### 路由(`App.tsx` 改 + `routes/` 新)

引入 `react-router-dom`,两条路由:
- `/` → `InterviewPage`(现有 App 内容迁移过去)
- `/manage` → `ManagePage`

面试页顶部加"管理"链接,管理页加"返回面试"链接。

#### `DocumentUpload.tsx`

- 文件选择按钮(`accept=".pdf,.md"`)
- 类型单选:`( ) 简历  ( ) 题库`
- 上传按钮 → 调 `POST /api/documents/upload`
- 上传后刷新列表

#### `DocumentList.tsx`

- 表格/列表展示:文件名 / 类型 / 大小 / 删除按钮
- 删除调 `DELETE /api/documents/{id}`

#### `useDocuments.ts`

- `list()` 拉取文档列表
- `upload(file, docType)` 上传
- `remove(id)` 删除
- 状态:文档列表 + loading + error

#### `api/documents.ts`

- `uploadDocument(file, docType)`:multipart POST
- `listDocuments()`:GET
- `deleteDocument(id)`:DELETE

## 关键设计决策汇总

| 决策点 | 选择 | 理由 |
|--------|------|------|
| RAG vs 上下文 | 直接塞上下文 | 几万字量级,塞进 128k 上下文更准更简单 |
| 文档格式 | PDF + Markdown | 简历 PDF,题库 .md |
| 类型选择 | 手动单选 | 明确可控,不靠后缀猜 |
| Markdown 处理 | 保留格式 | `#`/列表符号帮 LLM 理解结构 |
| 文件存储 | 不落盘,只存文本到内存 | 本期单用户单进程,简单 |
| 文档作用域 | 全局(跨 session) | 整场面试用同一份简历+题库 |
| 类型用途区分 | system prompt 分开标注 | 简历是素材,题库是优先答案 |
| 管理页形态 | 独立路由 /manage | 与面试页解耦 |
| 追问是否拼文档 | 拼 | 保持建议/追问上下文一致 |

## 依赖新增

**后端:**
- `pypdf`(PDF 文本提取)
- `python-multipart`(FastAPI 文件上传支持)

**前端:**
- `react-router-dom`(路由)

## 非目标(本期不做)

- 文档编辑(上传后不能改,只能删了重传)
- 多用户/账号体系(单用户单进程)
- 文件持久化(重启丢失,后续可加落盘/OSS)
- 文档全文搜索(直接塞上下文,不需要)
- 其它格式(doc/txt/html 等)
- 文档大小限制的精细策略(本期简单限制单文件 < 10MB)
