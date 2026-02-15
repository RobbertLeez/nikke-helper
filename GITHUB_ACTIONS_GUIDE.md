# GitHub Actions 自动打包 EXE 教程

## 📋 简介

本教程将指导您使用 GitHub Actions 自动打包 NIKKE CArena Helper 为 Windows EXE 文件。

**优势**：
- ✅ 完全在线打包，无需本地环境
- ✅ 自动化流程，推送代码即可
- ✅ 免费使用（GitHub Actions 免费额度）
- ✅ 支持多次打包

**前提条件**：
- 需要一个 GitHub 账号（免费注册）
- 基本的 Git 操作知识（或使用 GitHub 网页版）

---

## 🚀 快速开始（3步完成）

### 步骤1：创建 GitHub 仓库

#### 方法A：使用 GitHub 网页版（推荐新手）

1. 登录 [GitHub](https://github.com)
2. 点击右上角 `+` → `New repository`
3. 填写信息：
   - Repository name: `nikke-carena-helper`
   - Description: `NIKKE CArena Helper with Mode 10`
   - 选择 `Public` 或 `Private`（都可以）
4. 点击 `Create repository`

#### 方法B：使用 Git 命令行

```bash
# 在项目目录下
cd nikke-CArena-Helper-main
git init
git add .
git commit -m "Initial commit with Mode 10"
git branch -M main
git remote add origin https://github.com/你的用户名/nikke-carena-helper.git
git push -u origin main
```

### 步骤2：上传代码到 GitHub

#### 方法A：使用 GitHub 网页版上传

1. 进入刚创建的仓库页面
2. 点击 `uploading an existing file`
3. 将整个 `nikke-CArena-Helper-main` 文件夹拖拽到页面
4. 等待上传完成
5. 填写 Commit message: `Add Mode 10 auto recording`
6. 点击 `Commit changes`

#### 方法B：使用 GitHub Desktop（推荐）

1. 下载并安装 [GitHub Desktop](https://desktop.github.com/)
2. 登录 GitHub 账号
3. File → Add Local Repository → 选择 `nikke-CArena-Helper-main` 文件夹
4. 填写 Summary: `Add Mode 10`
5. 点击 `Commit to main`
6. 点击 `Push origin`

### 步骤3：触发自动打包

#### 自动触发（推荐）

代码推送后，GitHub Actions 会自动开始打包！

#### 手动触发

1. 进入仓库页面
2. 点击顶部 `Actions` 标签
3. 左侧选择 `Build Windows EXE`
4. 右侧点击 `Run workflow` 按钮
5. 点击绿色的 `Run workflow` 确认

---

## 📥 下载打包好的 EXE

### 等待打包完成

1. 进入仓库的 `Actions` 页面
2. 点击最新的工作流运行记录
3. 等待所有步骤完成（约5-10分钟）
4. 看到绿色的 ✅ 表示成功

### 下载 EXE 文件

1. 在工作流页面向下滚动到 `Artifacts` 部分
2. 点击 `NIKKE_CArena_Helper_EXE` 下载
3. 下载的是一个 ZIP 文件
4. 解压后得到 `NIKKE_CArena_Helper` 文件夹
5. 文件夹内有 `NIKKE_CArena_Helper.exe`

---

## 📁 文件结构说明

打包后的文件结构：

```
NIKKE_CArena_Helper/
├── NIKKE_CArena_Helper.exe  ← 主程序
├── config.json              ← 配置文件
├── assets/                  ← 资源文件夹
│   ├── 1.png
│   ├── 2.png
│   ├── ...
│   └── 10.png
└── _internal/               ← 依赖库（自动生成）
    └── ...
```

**使用方法**：
1. 解压整个文件夹到任意位置
2. 双击 `NIKKE_CArena_Helper.exe` 运行
3. 不要单独移动 EXE 文件，必须保持文件夹结构

---

## 🔧 高级配置

### 修改 GitHub Actions 配置

如果需要自定义打包流程，编辑 `.github/workflows/build-exe.yml`：

```yaml
# 修改 Python 版本
python-version: '3.11'  # 改为其他版本

# 添加更多依赖
pip install 你的库名

# 修改打包命令
pyinstaller 你的配置.spec
```

### 创建 Release 版本

如果想创建正式发布版本：

1. 在本地或 GitHub 网页创建 Tag：
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

2. GitHub Actions 会自动创建 Release
3. EXE 文件会自动附加到 Release 页面

---

## 📊 GitHub Actions 工作流程

```
推送代码到 GitHub
  ↓
触发 GitHub Actions
  ↓
在 Windows 虚拟机上运行
  ↓
安装 Python 3.11
  ↓
安装所有依赖库
  ↓
运行 PyInstaller 打包
  ↓
压缩打包结果
  ↓
上传为 Artifact
  ↓
完成！可以下载
```

**耗时**：约 5-10 分钟

---

## ❓ 常见问题

### Q1: 打包失败怎么办？

**A**: 查看错误日志：
1. 进入 Actions 页面
2. 点击失败的工作流
3. 点击红色的 ❌ 步骤
4. 查看详细错误信息

常见错误：
- **依赖安装失败**：检查 `requirements.txt` 是否正确
- **spec 文件错误**：检查 `NIKKE_CArena_Helper.spec` 语法
- **文件缺失**：确保所有文件都已上传

### Q2: 下载的文件在哪里？

**A**: 
1. Actions 页面 → 点击工作流
2. 向下滚动到 `Artifacts` 部分
3. 点击 `NIKKE_CArena_Helper_EXE` 下载

### Q3: 每次修改代码都要重新打包吗？

**A**: 是的，但是：
- 推送代码后自动打包，无需手动操作
- 可以在 Actions 页面手动触发
- 可以暂时禁用自动打包（修改 workflow 文件）

### Q4: GitHub Actions 免费吗？

**A**: 
- **公开仓库**：完全免费，无限制
- **私有仓库**：每月 2000 分钟免费额度
- 打包一次约 5-10 分钟，足够使用

### Q5: 可以打包成单文件 EXE 吗？

**A**: 可以，修改 `NIKKE_CArena_Helper.spec`：

```python
# 找到 EXE 部分，修改：
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # 添加这行
    a.zipfiles,      # 添加这行
    a.datas,         # 添加这行
    [],
    exclude_binaries=False,  # 改为 False
    name='NIKKE_CArena_Helper',
    # ... 其他配置
)

# 删除或注释掉 COLLECT 部分
```

但单文件 EXE 启动较慢，不推荐。

### Q6: 打包的 EXE 能在其他电脑运行吗？

**A**: 可以！打包后的 EXE 包含所有依赖，可以在任何 Windows 10/11 电脑上运行，无需安装 Python。

### Q7: 如何更新代码后重新打包？

**A**: 
1. 修改代码
2. 推送到 GitHub（或使用网页版上传）
3. 自动触发打包
4. 下载新的 EXE

---

## 🎯 完整操作示例

### 示例：首次使用 GitHub Actions

**场景**：您有源码，想打包成 EXE，但电脑没有 Python 环境。

**步骤**：

1. **注册 GitHub 账号**（如果没有）
   - 访问 https://github.com
   - 点击 Sign up
   - 填写信息注册

2. **创建仓库**
   - 登录后点击右上角 `+` → `New repository`
   - 名称：`nikke-helper`
   - 点击 `Create repository`

3. **上传代码**
   - 点击 `uploading an existing file`
   - 拖拽整个 `nikke-CArena-Helper-main` 文件夹
   - 等待上传完成
   - 点击 `Commit changes`

4. **等待自动打包**
   - 点击顶部 `Actions` 标签
   - 看到 `Build Windows EXE` 正在运行
   - 等待约 5-10 分钟

5. **下载 EXE**
   - 打包完成后，点击工作流名称
   - 向下滚动到 `Artifacts`
   - 点击 `NIKKE_CArena_Helper_EXE` 下载
   - 解压 ZIP 文件
   - 运行 `NIKKE_CArena_Helper.exe`

**完成！** 🎉

---

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [PyInstaller 文档](https://pyinstaller.org/)
- [GitHub Desktop 下载](https://desktop.github.com/)
- [Git 教程](https://git-scm.com/book/zh/v2)

---

## 🔒 隐私和安全

### 代码安全

- **公开仓库**：代码对所有人可见
- **私有仓库**：只有您和授权用户可见

**建议**：
- 如果代码包含敏感信息，使用私有仓库
- 不要在代码中硬编码密码或密钥
- 使用 GitHub Secrets 存储敏感配置

### Artifact 保留

- Artifacts 默认保留 30 天
- 可以在 workflow 文件中修改：
  ```yaml
  retention-days: 90  # 保留 90 天
  ```

---

## 💡 提示和技巧

### 技巧1：加速打包

在 workflow 文件中添加缓存：

```yaml
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~\AppData\Local\pip\Cache
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

### 技巧2：多版本打包

同时打包多个 Python 版本：

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

### 技巧3：自动发布到 Release

创建 Tag 时自动发布：

```bash
git tag -a v1.2.0 -m "Release v1.2.0 with Mode 10"
git push origin v1.2.0
```

### 技巧4：添加构建徽章

在 README.md 中添加：

```markdown
![Build Status](https://github.com/你的用户名/nikke-helper/workflows/Build%20Windows%20EXE/badge.svg)
```

---

## 📞 获取帮助

如果遇到问题：

1. 查看本教程的常见问题部分
2. 查看 GitHub Actions 日志
3. 搜索 GitHub Actions 文档
4. 在项目 Issues 中提问

---

**版本**: 1.0  
**更新日期**: 2026-02-15  
**作者**: Manus AI
