# NIKKE CArena Helper 模式10部署指南

## 快速部署步骤

### 1. 解压源码包
```bash
unzip NIKKE_CArena_Helper_with_Mode10.zip
cd nikke-CArena-Helper-main
```

### 2. 安装依赖（如果需要）
```bash
pip install -r requirements.txt
```

主要依赖：
- customtkinter
- opencv-python
- numpy
- pyautogui
- pygetwindow
- pywin32
- psutil
- keyboard
- pillow
- pyyaml

### 3. 测试运行
```bash
python gui_app.py
```

### 4. 打包为可执行文件
```bash
pyinstaller NIKKE_CArena_Helper.spec
```

生成的可执行文件位于：`dist/NIKKE_CArena_Helper/`

## 文件结构说明

```
nikke-CArena-Helper-main/
├── app.py                    # 应用核心逻辑
├── gui_app.py                # GUI入口
├── config.json               # 配置文件（已添加mode10配置）
├── MODE10_README.md          # 模式10用户文档
├── core/                     # 核心功能模块
│   ├── constants.py          # 常量定义
│   ├── utils.py              # 工具函数
│   ├── player_processing.py  # 玩家数据处理
│   └── match_processing.py   # 比赛数据处理
├── modes/                    # 各模式实现
│   ├── mode1.py              # 模式1-9
│   ├── ...
│   └── mode10.py             # 新增：自动录屏模式
├── gui/                      # GUI组件
├── assets/                   # 资源文件
│   ├── 1.png - 9.png
│   ├── 10.png                # 新增：模式10图标
│   └── 41.png
└── icon.ico                  # 应用图标
```

## 配置说明

### config.json 新增内容

#### 模式配置
```json
"mode10": {
  "output_filename_suffix": "_recording",
  "num_matches": 5,
  "start_match": 0,
  "video_fps": 60,
  "video_resolution_width": 1920,
  "video_resolution_height": 1080
}
```

#### 模式元数据
```json
{
  "id": 10,
  "name": "自动录屏",
  "desc": "自动点击播放按钮，录制对局回放视频，检测结果页面后停止录屏。",
  "enabled": true,
  "asset_image": "10.png"
}
```

## 调整播放按钮位置

如果默认按钮位置不准确，编辑 `modes/mode10.py`：

```python
play_button_coords_rel = [
    (0.85, 0.35),  # Round 01 - 调整这些值
    (0.85, 0.45),  # Round 02
    (0.85, 0.55),  # Round 03
    (0.85, 0.65),  # Round 04
    (0.85, 0.75),  # Round 05
]
```

### 如何确定正确坐标：

1. **运行游戏并截图**
   - 打开对局结果页面
   - 截取完整窗口

2. **测量按钮位置**
   - 使用图像编辑器打开截图
   - 测量窗口宽度和高度
   - 测量按钮中心的X、Y坐标
   - 计算相对坐标：
     - X_rel = X_像素 / 窗口宽度
     - Y_rel = Y_像素 / 窗口高度

3. **更新代码**
   - 修改 `play_button_coords_rel` 中的值
   - 保存文件
   - 重新运行测试

## 调整结果检测

如果结果页面检测不准确，编辑 `modes/mode10.py` 中的 `detect_result_screen` 函数：

### 调整检测区域
```python
# 当前值：检测窗口上方40%的区域
result_detection_region_rel = (0.1, 0.15, 0.8, 0.4)
# 格式：(左, 上, 宽度, 高度) - 相对坐标
```

### 调整颜色阈值
```python
# HSV颜色范围（蓝色）
lower_blue = np.array([100, 50, 50])   # 降低第一个值可以检测更多蓝色
upper_blue = np.array([130, 255, 255]) # 提高第一个值可以限制蓝色范围
```

### 调整判断阈值
```python
# 当前：蓝色占比超过30%认为是结果页面
if blue_ratio > 0.3:  # 可以调整为0.2-0.5之间
```

## 性能优化建议

### 降低CPU占用
```json
"video_fps": 30,  // 从60降到30
```

### 降低文件大小
```json
"video_resolution_width": 1280,
"video_resolution_height": 720
```

### 只录制特定场次
```json
"num_matches": 1,     // 只录制1场
"start_match": 0      // 从第1场开始（0-4）
```

## 常见问题解决

### 问题1：导入错误
```
ModuleNotFoundError: No module named 'cv2'
```
**解决**：
```bash
pip install opencv-python
```

### 问题2：权限错误
```
PermissionError: [WinError 5] 拒绝访问
```
**解决**：以管理员权限运行程序

### 问题3：窗口未找到
```
错误：未找到正在运行的进程 'nikke.exe'
```
**解决**：
1. 确保游戏已启动
2. 检查进程名是否为 `nikke.exe`
3. 如果不是，修改 `core/constants.py` 中的 `TARGET_PROCESS_NAME`

### 问题4：录制黑屏
**原因**：窗口被其他窗口遮挡或最小化
**解决**：
1. 确保游戏窗口在前台
2. 不要最小化窗口
3. 关闭其他覆盖窗口

## 测试清单

在部署前，请完成以下测试：

- [ ] 程序能正常启动
- [ ] 能找到并激活游戏窗口
- [ ] 能正确点击第1个播放按钮
- [ ] 能正确点击第2-5个播放按钮
- [ ] 录制功能正常工作
- [ ] 能检测到结果页面
- [ ] 能自动停止录制
- [ ] 视频文件正常保存
- [ ] 视频内容完整可播放
- [ ] 能连续录制多场对局
- [ ] 停止信号响应正常
- [ ] 超时机制工作正常

## 打包发布

### 使用 PyInstaller
```bash
# 确保已安装 PyInstaller
pip install pyinstaller

# 使用项目配置文件打包
pyinstaller NIKKE_CArena_Helper.spec

# 打包完成后
cd dist/NIKKE_CArena_Helper/
```

### 发布包内容
```
NIKKE_CArena_Helper/
├── NIKKE_CArena_Helper.exe
├── config.json
├── MODE10_README.md
├── assets/
│   └── *.png
└── _internal/
    └── (依赖库)
```

### 压缩发布
```bash
cd dist
zip -r NIKKE_CArena_Helper_v2.0.zip NIKKE_CArena_Helper/
```

## 版本信息

- **版本号**: 2.0.0
- **新增功能**: 模式10 - 自动录屏
- **发布日期**: 2026-02-15
- **兼容性**: Windows 10/11

## 技术支持

如遇到问题：
1. 查看 `MODE10_README.md` 中的故障排除部分
2. 检查日志文件（如果启用了日志）
3. 提供详细的错误信息和截图

---

**重要提示**：
- 首次使用请先测试单场录制
- 确保有足够的磁盘空间（每场约100-300MB）
- 建议以管理员权限运行
- 录制期间不要最小化游戏窗口
