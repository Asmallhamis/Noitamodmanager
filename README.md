# Noita Mod Manager (Noita 模组管理器)

一个轻量级的 Noita 模组管理工具，专为解决 Steam 创意工坊模组在离线或非 Steam 启动环境下无法加载的问题而设计。

[English](#english) | [中文](#chinese)

---

<a name="chinese"></a>
## ✨ 功能特点

*   **离线支持**：自动将创意工坊模组转换为本地软链接 (Symlink)，欺骗游戏直接读取，无需 Steam 启动即可加载工坊模组。
*   **拖拽排序**：支持鼠标拖拽调整模组加载顺序。
*   **预设系统**：可保存多套模组配置，并生成桌面快捷方式一键启动特定配置。
*   **智能识别**：自动识别本地模组、工坊副本和工坊软链接。
*   **零依赖**：基于 Python 标准库编写，无需安装任何第三方库，开箱即用。

## 🚀 使用说明

1.  **环境要求**：确保已安装 [Python](https://www.python.org/downloads/) (推荐 3.8 或更高版本)。
2.  **运行**：双击运行 `NoitaModManager.py`。
3.  **首次设置**：程序会自动检测游戏路径。如果检测失败，请根据提示手动选择 `Noita` 游戏目录和创意工坊目录。
4.  **同步模组**：点击右上角的 [同步创意工坊] 按钮。
    *   建议选择 "是" 将本地副本转换为软链接，这样既节省空间又能保持模组更新。
5.  **启用模组**：在列表中勾选想要启用的模组。
    *   拖拽模组名称可以调整加载顺序。
6.  **启动游戏**：点击 [启动游戏] 即可。

## 📦 分发/安装

只需下载以下文件即可运行：
*   `NoitaModManager.py`

---

<a name="english"></a>
## ✨ Features

*   **Offline Support**: Automatically converts Workshop mods to local symlinks, allowing the game to load them without Steam running.
*   **Drag & Drop Sorting**: Easily reorder mods by dragging.
*   **Presets**: Save/Load mod configurations and create desktop shortcuts for instant launching.
*   **Zero Dependencies**: Written in pure Python (Standard Library), no `pip install` needed.

## 🚀 How to Use

1.  Install [Python](https://www.python.org/downloads/).
2.  Run `NoitaModManager.py`.
3.  Follow the setup prompt to locate your Noita game folder if not detected automatically.
4.  Click "Sync Workshop" to link your subscribed mods.
5.  Check the mods you want to enable.
6.  Click "Launch Game".
