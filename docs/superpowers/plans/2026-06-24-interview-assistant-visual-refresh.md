# 面试助手前端视觉优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将面试助手升级为清爽智能的固定左右双栏桌面界面，同时保持全部现有采集、字幕、建议与追问行为不变。

**Architecture:** 仅调整 React 组件的语义 className 和 CSS 呈现层。`App.tsx` 继续编排现有钩子与错误状态；`Controls`、`SubtitlePanel`、`SuggestPanel` 各自渲染一个视觉卡片区域；`index.css` 集中定义设计令牌和样式，避免组件中散落内联样式。

**Tech Stack:** React 18、TypeScript、Vite 5、原生 CSS。

---

## 文件结构

- Modify: `frontend/src/index.css` — 全局设计令牌、固定左右布局、工具栏、卡片、按钮、字幕和追问样式。
- Modify: `frontend/src/App.tsx` — 用语义 className 取代页面级内联布局，并保留现有业务钩子。
- Modify: `frontend/src/components/Controls.tsx` — 顶部工具栏、采集状态胶囊和常驻操作按钮。
- Modify: `frontend/src/components/SubtitlePanel.tsx` — 左侧实时字幕卡片、空状态与识别中状态。
- Modify: `frontend/src/components/SuggestPanel.tsx` — 右侧回答建议卡片、建议容器、追问历史与底部输入区。

### Task 1: 建立全局视觉令牌与固定双栏骨架

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: 写入最小可验证的页面骨架样式**

在 `frontend/src/index.css` 添加下列样式，使页面在没有业务数据时也呈现背景、卡片和横向滚动策略：

```css
:root {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: #18233f;
  background: #f7f8fd;
  font-synthesis: none;
}

* { box-sizing: border-box; }

body { margin: 0; min-width: 980px; }

.app-shell {
  min-width: 980px;
  min-height: 100vh;
  padding: 24px;
  background: radial-gradient(circle at 12% 4%, #e8edff 0, transparent 30%), #f7f8fd;
}

.workspace {
  min-height: calc(100vh - 128px);
  display: grid;
  grid-template-columns: minmax(0, 44fr) minmax(0, 56fr);
  gap: 18px;
}
```

- [ ] **Step 2: 构建以验证 CSS 未破坏 TypeScript/Vite 管线**

Run: `npm run build`

Expected: 命令以退出码 0 结束，并输出 `✓ built in`。

- [ ] **Step 3: 补齐工具栏、卡片与焦点通用样式**

继续在 `index.css` 添加以下基础规则，后续组件只使用这些 className：

```css
.topbar, .panel-card { border: 1px solid #e5e9f7; background: rgba(255, 255, 255, .9); }
.panel-card { min-width: 0; min-height: 0; border-radius: 16px; overflow: hidden; }
button:focus-visible, input:focus-visible { outline: 3px solid rgba(86, 106, 221, .35); outline-offset: 2px; }
button { font: inherit; cursor: pointer; }
```

- [ ] **Step 4: 再次构建确认样式规则有效**

Run: `npm run build`

Expected: 命令以退出码 0 结束。

- [ ] **Step 5: 提交全局样式骨架**

```bash
git add frontend/src/index.css
git commit -m "style: add interview assistant visual foundation"
```

### Task 2: 改造页面壳与顶部常驻操作栏

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Controls.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: 将 App 页面级内联样式替换为语义结构**

将 `App.tsx` 的返回结构替换为以下骨架，不修改 `subtitle`、`chat`、`onStart`、`onStop`、`onSuggest` 或 `onClear` 的现有逻辑：

```tsx
return (
  <main className="app-shell">
    <div className="app-frame">
      <Controls
        isCapturing={isCapturing}
        onStart={onStart}
        onStop={onStop}
        onSuggest={onSuggest}
        onClear={onClear}
      />
      {(captureError || subtitle.error) && (
        <div className="error-banner" role="alert">
          {captureError || subtitle.error}
        </div>
      )}
      <section className="workspace" aria-label="面试辅助工作区">
        <SubtitlePanel lines={subtitle.lines} currentPartial={subtitle.currentPartial} />
        <SuggestPanel
          suggestion={chat.suggestion}
          loading={chat.loading}
          streaming={chat.streaming}
          followups={chat.followups}
          error={chat.error}
          onAsk={chat.ask}
        />
      </section>
    </div>
  </main>
)
```

- [ ] **Step 2: 让 Controls 渲染状态胶囊与常驻按钮**

将 `Controls.tsx` 的外层改为 `header.topbar`；为标题增加图标容器；用 `isCapturing` 渲染以下状态文案；所有按钮都保留在 DOM 内：

```tsx
<div className={`capture-status ${isCapturing ? 'is-active' : ''}`}>
  <span aria-hidden="true" className="status-dot" />
  {isCapturing ? '正在采集' : '等待采集'}
</div>
```

采集按钮使用 className `primary-control`，生成建议使用 `accent-control`，清空使用 `secondary-control`。按钮原有 `onClick` 回调和文字保持不变。

- [ ] **Step 3: 添加 App 与工具栏对应样式**

在 `index.css` 添加 `.app-frame`、`.topbar`、`.brand`、`.capture-status`、`.status-dot`、`.primary-control`、`.accent-control`、`.secondary-control` 和 `.error-banner`，并确保：

```css
.topbar { min-height: 76px; display: flex; align-items: center; gap: 10px; padding: 0 24px; border-radius: 18px; }
.brand { margin-right: auto; font-size: 17px; font-weight: 760; }
.capture-status { border-radius: 999px; padding: 7px 10px; color: #687594; background: #f1f3fa; font-size: 12px; }
.capture-status.is-active { color: #5368d5; background: #eef1ff; }
.accent-control { color: #fff; border-color: #566add; background: #566add; }
```

- [ ] **Step 4: 运行构建验证组件 props 与 className 无误**

Run: `npm run build`

Expected: 命令以退出码 0 结束，无 TypeScript error。

- [ ] **Step 5: 提交页面壳与工具栏**

```bash
git add frontend/src/App.tsx frontend/src/components/Controls.tsx frontend/src/index.css
git commit -m "style: refresh interview assistant controls"
```

### Task 3: 改造左右内容卡片与追问输入区

**Files:**
- Modify: `frontend/src/components/SubtitlePanel.tsx`
- Modify: `frontend/src/components/SuggestPanel.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: 重构 SubtitlePanel 的语义 className**

保留 `bottomRef`、`useEffect` 和现有字幕数据循环，将 JSX 结构改为：

```tsx
<section className="panel-card subtitle-card" aria-label="实时字幕">
  <header className="panel-header"><h2>实时字幕</h2><span>自动滚动</span></header>
  <div className="subtitle-content">
    {lines.length === 0 && !currentPartial && <p className="empty-state">点“开始采集”后，面试官的话会出现在这里。</p>}
    {lines.map((line, index) => <p className="subtitle-line" key={index}>{line.text}</p>)}
    {currentPartial && <p className="subtitle-partial"><strong>识别中</strong>{currentPartial}</p>}
    <div ref={bottomRef} />
  </div>
</section>
```

- [ ] **Step 2: 重构 SuggestPanel 的建议与追问区域 className**

保留 `input` state 与 `send` 函数。外层使用 `section.panel-card.suggest-card`；建议内容放入 `.suggestion-box`；追问记录使用 `.followup-message` 和角色修饰 className；输入区使用 `form.ask-form`。`form` 的 `onSubmit` 需调用 `event.preventDefault()` 后执行 `send()`，从而继续支持 Enter 并避免页面刷新。

- [ ] **Step 3: 添加卡片内容样式**

在 `index.css` 添加下列关键规则：

```css
.panel-header { display: flex; align-items: center; padding: 16px 18px; border-bottom: 1px solid #edf0fa; }
.panel-header h2 { margin: 0; font-size: 14px; }
.panel-header span { margin-left: auto; color: #8d99b6; font-size: 12px; }
.subtitle-content, .suggestion-content { min-height: 0; overflow-y: auto; padding: 18px; }
.empty-state { color: #8d99b6; line-height: 1.7; }
.subtitle-partial, .suggestion-box { border: 1px solid #e0e6fb; border-radius: 12px; background: #f3f5ff; }
.ask-form { display: flex; gap: 8px; padding: 14px 18px; border-top: 1px solid #edf0fa; }
.ask-form input { flex: 1; min-width: 0; }
```

- [ ] **Step 4: 运行构建验证追问表单与 JSX 类型**

Run: `npm run build`

Expected: 命令以退出码 0 结束。

- [ ] **Step 5: 提交内容卡片**

```bash
git add frontend/src/components/SubtitlePanel.tsx frontend/src/components/SuggestPanel.tsx frontend/src/index.css
git commit -m "style: polish interview assistant panels"
```

### Task 4: 验证固定左右布局与现有功能

**Files:**
- Modify: `frontend/src/index.css`（仅当验证发现视觉缺陷时）

- [ ] **Step 1: 启动本地前端**

Run: `npm run dev -- --host 127.0.0.1`

Expected: 输出包含本地访问地址，通常为 `http://localhost:5173/`。

- [ ] **Step 2: 检查空状态与工具栏**

在浏览器打开 `http://localhost:5173/`，确认左侧是“实时字幕”空状态，右侧是“回答建议”空状态；顶部开始采集、生成建议和清空按钮均可见。

- [ ] **Step 3: 检查固定左右双栏**

将浏览器窗口缩窄，确认字幕仍在左、回答建议仍在右；页面允许横向滚动，但不得把两张卡片改为上下堆叠。

- [ ] **Step 4: 检查可交互状态**

点击“开始采集”后，确认顶部状态变为“正在采集”且采集按钮变为“停止采集”；触发生成建议、清空、追问输入和错误提示时，确认现有业务逻辑继续工作，文字可读且不会遮挡内容。

- [ ] **Step 5: 运行最终构建**

Run: `npm run build`

Expected: 命令以退出码 0 结束，并输出 `✓ built in`。

- [ ] **Step 6: 提交最终视觉调整**

```bash
git add frontend/src/index.css frontend/src/App.tsx frontend/src/components/Controls.tsx frontend/src/components/SubtitlePanel.tsx frontend/src/components/SuggestPanel.tsx
git commit -m "style: finalize interview assistant visual refresh"
```
