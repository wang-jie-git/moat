# Moat 社交预览图设计规范

## 设计要点

### 视觉风格
- **极简主义**: 少即是多
- **品牌色**: 蓝色 (#2196F3) + 护城河意象
- **字体**: 现代无衬线字体
- **背景**: 渐变或纯色

### 文案
```
Moat
AI 编码护城河
```

或

```
Prevent AI from breaking your code
12 seconds | Four-layer defense
```

### 规格
- **尺寸**: 1280×640px (GitHub 推荐)
- **格式**: PNG (背景) + SVG (文字)
- **文件**: `docs/assets/social-preview.png`

### 工具
- **Figma**: https://www.figma.com
- **Canva**: https://www.canva.com
- **Pitch**: https://pitch.com

## 参考设计

### 方案 1: 护城河意象
```
背景: 深蓝色渐变 (#1565C0 → #0D47A1)
中间: 简化的城堡 + 护城河图标
顶部: "Moat" (大号白色字体)
底部: "AI Coding Guardrails" (中等白色字体)
角落: GitHub 图标 + Python logo
```

### 方案 2: 代码保护意象
```
背景: 深灰色 (#212121)
左侧: 盾牌图标 (保护符号)
右侧: 代码片段 (before/after 对比)
顶部: "Moat" (蓝色渐变字体)
底部: "Prevent AI from breaking your codebase"
```

### 方案 3: 极简主义
```
背景: 纯白或纯黑
中央: "Moat" 巨大字体 (蓝色)
下方: 四层防线图标 (L0-L4)
角落: MIT License 标志
```

## 创建步骤

1. 使用 Figma/Canva 创建 1280×640 画布
2. 选择配色方案
3. 添加文字和图标
4. 导出 PNG (2x)
5. 保存到 `docs/assets/social-preview.png`
6. 在 GitHub 仓库设置中上传

## 使用

上传后,所有分享链接将自动显示预览图:
- https://github.com/wang-jie-git/moat
- https://pypi.org/project/moat-ai/
