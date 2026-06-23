# Skill: 前端页面开发与维护

## 用途

处理本项目的前端页面开发、样式调整和交互功能开发。

## 何时使用

- 需要新增/修改前端页面时
- 需要调整 UI 样式时
- 需要添加新的交互功能时
- 需要修复前端 bug 时

## 页面清单

| 页面 | 文件 | 数据源 | 功能 |
|------|------|--------|------|
| 首页 | `index.html` | `data/news_data.json` | 综合新闻列表，一键复制 |
| GitHub | `github.html` | `data/github.json` | 9 个分类的热门项目 |
| Hacker News | `hackernews.html` | `data/hackernews.json` | HN 热榜 |
| 掘金 | `juejin.html` | `data/juejin.json` | 掘金热文 |

## 设计规范

### 设计风格
- **Airbnb 风格**：圆角、阴影、柔和配色
- **主色调**：`#FF5A5F` (rausch) — 爱彼迎红
- **字体**：系统字体栈，优先 PingFang SC / Microsoft YaHei

### CSS 变量
所有页面统一使用以下 CSS 变量：
```css
:root {
  --rausch: #FF5A5F;        /* 主色 */
  --rausch-dark: #E00E2F;   /* 深色主色 */
  --text-primary: #222222;  /* 主要文字 */
  --text-secondary: #717171;/* 次要文字 */
  --text-tertiary: #B0B0B0; /* 三级文字 */
  --bg: #FFFFFF;            /* 背景 */
  --bg-secondary: #F7F7F7;  /* 次级背景 */
  --border: #EBEBEB;        /* 边框 */
  --success: #00A699;       /* 成功色 */
  --radius: 12px;           /* 大圆角 */
  --radius-sm: 8px;         /* 小圆角 */
  --max-width: 1280px;      /* 最大宽度 */
}
```

### 组件复用

所有页面必须复用以下公共组件：

| 组件 | 文件 | 引入方式 |
|------|------|---------|
| 页头（日期+天气） | `scripts/header-info.js` | `<script src="scripts/header-info.js">` |
| 页脚（名言+链接） | `scripts/footer.js` | `<script src="scripts/footer.js">` |

**页头要求**：页面必须有 `id="header-subtitle"` 的元素用于显示日期时间

**页脚要求**：页面必须有 `class="footer"` 的元素

### 导航栏
所有页面顶部导航栏保持一致：
- 新闻 → `index.html`
- GitHub → `github.html`
- Hacker News → `hackernews.html`
- 掘金 → `juejin.html`

当前页面对应的导航链接添加 `active` 类。

## 数据加载模式

```javascript
fetch('data/xxx.json?t=' + Date.now())  // 时间戳防缓存
  .then(r => r.json())
  .then(data => {
    // 渲染数据
  })
  .catch(err => {
    console.error('加载失败:', err);
    // 渲染空状态或降级内容
  });
```

## 响应式断点

```css
/* 移动端：< 600px */
@media (max-width: 600px) {
  /* 移动端适配 */
}
```

## 新增页面 Checklist

- [ ] 复制现有页面结构作为模板
- [ ] 引入 `header-info.js` 和 `footer.js`
- [ ] 导航栏 active 类设置正确
- [ ] CSS 变量与设计规范一致
- [ ] 数据加载有错误处理和空状态
- [ ] 移动端响应式适配
- [ ] 数据使用时间戳防缓存
