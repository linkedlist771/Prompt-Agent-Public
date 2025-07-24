 # Prompt Agent Chrome Extension

一个优化你使用AI时候的prompt智能体Chrome扩展版本。

## 功能特性

- 🤖 支持多个AI聊天网站：DeepSeek、ChatGPT、Claude、Gemini
- ⚡ Ctrl+Enter快捷键快速发送请求
- 🔧 可配置API Key和启用/禁用状态
- 📱 简洁的弹出窗口界面
- 💾 跨域名设置同步
- 🌊 支持流式响应显示

## 安装方法

### 开发者模式安装

1. 打开Chrome浏览器
2. 访问 `chrome://extensions/`
3. 开启右上角的"开发者模式"
4. 点击"加载已解压的扩展程序"
5. 选择包含这些文件的`chrome_extension`文件夹
6. 扩展将出现在扩展列表中

### 文件结构
```
chrome_extension/
├── manifest.json      # 扩展配置文件
├── popup.html        # 弹出窗口界面
├── popup.js          # 弹出窗口逻辑
├── content.js        # 内容脚本
├── background.js     # 后台服务脚本
├── icon.png          # 扩展图标（需要自行添加）
└── README.md         # 说明文档
```

## 使用方法

### 首次设置

1. 点击浏览器工具栏中的Prompt Agent图标
2. 在弹出窗口中输入你的API Key
3. 勾选"启用AI响应"复选框
4. 点击"测试连接"确认设置正确

### 使用方式

#### 方式一：快捷键（推荐）
1. 在支持的AI网站输入框中输入你的问题
2. 按 `Ctrl + Enter` 快速发送请求
3. AI响应会自动替换你的输入内容

#### 方式二：手动发送
1. 在支持的AI网站输入框中输入你的问题
2. 点击扩展图标打开弹出窗口
3. 点击"手动发送"按钮

### 支持的网站

- [DeepSeek Chat](https://chat.deepseek.com/)
- [ChatGPT](https://chatgpt.com/)
- [Claude AI](https://claude.ai/)
- [Google Gemini](https://gemini.google.com/)
- [豆包](https://doubao.com/chat/)
- [Grok](https://grok.com/)
- [千问](https://tongyi.com/)
- [混元](https://hunyuan.tencent.com/)

## 配置选项

### API设置
- **API Key**: 你的API访问密钥
- **API端点**: `http://127.0.0.1:3648/api/v1/chat/completions`

### 功能选项
- **启用AI响应**: 开启/关闭扩展功能
- **测试连接**: 验证API Key和网络连接
- **重置设置**: 清除所有保存的配置

## 技术说明

### 主要技术栈
- Chrome Extension Manifest V3
- Chrome Storage API (跨域名同步)
- Content Scripts (页面交互)
- Service Worker (后台处理)

### 与UserScript的区别
1. **存储机制**: 使用Chrome Storage API替代GM_setValue/GM_getValue
2. **UI界面**: 使用Chrome Extension弹出窗口替代浮动UI
3. **权限模型**: 基于Chrome扩展权限系统
4. **生命周期**: Service Worker替代传统的后台脚本

### 文本输入模拟
扩展会智能识别不同网站的输入框类型：

| 网站 | 输入方法 | 特点 |
|------|----------|------|
| DeepSeek | 模拟键盘输入 | 逐字符模拟 |
| ChatGPT | React兼容模式 | 触发React事件 |
| Claude | 模拟键盘输入 | 逐字符模拟 |
| Gemini | CSP兼容模式 | 剪贴板API优先 |
| 豆包 | 直接输入模式 | 直接设置textarea.value |
| Grok | 直接输入模式 | 直接设置textarea.value |
| 千问 | 直接输入模式 | 直接设置textarea.value |
| 混元 | 直接输入模式 | 直接设置textarea.value |

**流式响应处理**：
- 对于`textarea`元素: 使用`.value`属性追加内容
- 对于`contenteditable`元素: 使用`textContent`属性
- 自动光标定位和滚动到底部

## 开发说明

### 调试方法
1. 在`chrome://extensions/`页面点击"检查视图"
2. 使用开发者工具调试popup.js和background.js
3. 在网页上按F12调试content.js

### 修改API端点
在content.js中修改`API_CONFIG.endpoint`变量。

### 添加新网站支持
在`SITE_CONFIGS`对象中添加新的网站配置。

## 故障排除

### 常见问题

1. **扩展无法加载**
   - 确认所有文件都在同一文件夹中
   - 检查manifest.json语法是否正确

2. **API连接失败**
   - 检查API Key是否正确
   - 确认网络连接正常
   - 验证API端点地址

3. **快捷键不工作**
   - 确认扩展已启用
   - 检查当前网站是否受支持
   - 确认输入框已聚焦

4. **内容脚本无法注入**
   - 刷新页面重试
   - 检查网站URL是否在支持列表中

### 错误日志
打开开发者工具查看控制台错误信息：
- 扩展相关错误会显示"Prompt Agent"前缀
- 网络请求错误会显示详细的HTTP状态码

## 更新日志

### v0.0.7
- 转换自UserScript版本
- 实现Chrome Extension Manifest V3支持
- 添加弹出窗口界面
- 集成Chrome Storage API

## 许可证

MIT License

## 支持

- 项目主页: https://github.com/linkedlist771/prompt-agent
- 问题反馈: https://github.com/linkedlist771/prompt-agent/issues