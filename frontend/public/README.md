# UPS Guard Logo资源使用说明

## 📁 文件说明

本目录包含UPS Guard logo设计相关的资源文件。

**开发者**：（王.W）

### logo-template.svg
- SVG矢量模板
- 512x512尺寸
- 包含盾牌、闪电、电池元素
- 蓝绿渐变专业配色
- 可在设计工具中编辑

## 🎨 如何使用

### 方法1：直接使用SVG
```html
<!-- 在HTML中使用 -->
<img src="/logo-template.svg" alt="UPS Guard" width="64" height="64">
```

### 方法2：转换为PNG

#### 在线转换
1. 访问 [CloudConvert](https://cloudconvert.com/svg-to-png)
2. 上传 `logo-template.svg`
3. 设置宽度和高度为 512px
4. 下载PNG文件

#### 使用Inkscape（免费）
```bash
# 命令行转换
inkscape logo-template.svg --export-type=png --export-width=512 --export-height=512 --export-filename=logo.png
```

#### 使用ImageMagick
```bash
# 命令行转换
convert -background none -resize 512x512 logo-template.svg logo.png
```

### 方法3：在设计工具中编辑

#### Figma
1. 创建新文件（512x512）
2. 导入 `logo-template.svg`
3. 编辑和优化
4. 导出为PNG（2x分辨率）

#### Adobe Illustrator
1. 打开 `logo-template.svg`
2. 编辑设计
3. 文件 → 导出 → 导出为PNG
4. 设置512x512px

#### Inkscape（免费）
1. 打开 `logo-template.svg`
2. 编辑图形
3. 文件 → 导出PNG图像
4. 宽度512，高度512

## 🔄 生成多种尺寸

```bash
# 使用ImageMagick批量生成
convert logo.png -resize 256x256 logo-256.png
convert logo.png -resize 128x128 logo-128.png
convert logo.png -resize 64x64 logo-64.png
convert logo.png -resize 32x32 logo-32.png

# 生成favicon
convert logo.png -resize 32x32 favicon.ico
```

## 📋 推荐的文件命名

```
logo.svg          - 原始SVG矢量文件
logo.png          - 512x512 主logo
logo-256.png      - 256x256 中等尺寸
logo-128.png      - 128x128 小尺寸
logo-64.png       - 64x64 图标
logo-32.png       - 32x32 最小图标
favicon.ico       - 网站图标
logo-light.png    - 浅色背景版本
logo-dark.png     - 深色背景版本
```

## 🎯 使用场景

### Web应用
- Dashboard标题栏：64x64
- 登录页面：256x256
- Favicon：32x32

### 文档
- README.md：128x128
- 用户手册：512x512

### 社交媒体
- GitHub头像：512x512
- Twitter：400x400

## 💡 设计提示

如果你要修改模板：

1. **颜色调整**：修改SVG中的渐变定义
2. **元素修改**：编辑SVG路径和形状
3. **文字更新**：修改`<text>`标签内容
4. **导出透明**：确保背景是透明的

## 🆘 需要帮助？

- 查看 `docs/zh/logo-design-guide.md` 获取完整设计指南
- 使用AI工具（DALL-E, Midjourney）生成新设计
- 雇佣专业设计师（Fiverr, Upwork）

## 📌 注意事项

- ✅ 保持透明背景
- ✅ 确保在小尺寸（32px）时仍可识别
- ✅ 测试在浅色和深色背景上的效果
- ✅ 保存高分辨率原文件（SVG或AI格式）

---

更多信息请参考 [Logo设计指南](../../docs/zh/logo-design-guide.md)
