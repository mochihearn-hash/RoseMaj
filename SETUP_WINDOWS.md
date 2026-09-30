# RoseMaj — Windows 本地环境搭建教程

> 本教程基于本机（WORKPC）实测结果编写，路径和版本都是这台机器的真实情况。
> 每一步都可以直接复制粘贴到 PowerShell 里执行。
>
> 最后更新：环境已搭建完成并验证通过（19 个测试全绿）。

---

## 0. 先搞清楚本机的三个坑

在动手前必须知道这三件事，否则一定会踩坑：

| 坑 | 实际情况 | 后果 |
|---|---|---|
| **默认 `python` 太旧** | `python` → `C:\Users\wangy\Anaconda3\python.exe`，版本 **3.7.0** | 项目要求 `>=3.9`，直接用 `python` 命令会报错 |
| **`.bat` 里写死了别人的路径** | `RoseliaMahjong_GUI.bat` / `run_online_server.bat` 里写的是 `F:\anaconda3\python.exe` | 本机**没有 F 盘**，会静默退回用 3.7 那个 python，然后失败 |
| **系统开着代理** | `127.0.0.1:7897`（Clash Verge 一类） | pip 直连 PyPI 可能很慢或卡住，建议走国内镜像 |

**本机可用的正确 Python：**

```text
C:\Users\wangy\AppData\Local\Programs\Python\Python312\python.exe   (3.12.10)
```

**已经建好的虚拟环境：**

```text
D:\projects\RoseMaj\.venv      ← Python 3.12.10，pip 25.0.1，依赖已装齐
```

> 记住一个原则：**这个项目里不要用裸 `python` 命令**，要么用虚拟环境的完整路径，
> 要么先激活虚拟环境。下面统一用完整路径，最不容易出错。

---

## 1. 打开一个普通终端

按 `Win + X`，选「终端」或「Windows PowerShell」。

> 不要用管理员权限，也不需要。普通窗口就够。

---

## 2. 清理 pip 留下的空壳目录

pip 中断时可能在**仓库根目录**留下一批空的 `pip-xxxx` 目录，
它们不属于项目、也没被 `.gitignore` 覆盖，会让 `git status` 刷一堆警告。

先**预览**（只列不删）：

```powershell
cd D:\projects\RoseMaj
Get-ChildItem -Directory -Filter 'pip-*' | Select-Object -ExpandProperty Name
```

确认列出来的都是 `pip-unpack-xxxx` / `pip-install-xxxx` / `pip-build-tracker-xxxx` /
`pip-ephem-wheel-cache-xxxx` 这种名字后，再删：

```powershell
Get-ChildItem -Directory -Filter 'pip-*' | Remove-Item -Recurse -Force
```

> 上面这条是**管道写法**：先筛出以 `pip-` 开头的目录，再把它们交给 `Remove-Item`。
> 它永远不会碰到项目文件，也不会碰到父目录——比手写路径安全得多。

删完再 `git status` 应该干干净净、一句警告都没有。

### 关于 `.tmp` 目录

如果你之前手动跑过带自定义 `TEMP` 的命令，可能还会看到 `.tmp` 目录：

```powershell
Get-ChildItem 'D:\projects\RoseMaj\.tmp','D:\projects\.tmp' -Force -ErrorAction SilentlyContinue
```

有就同样删掉：

```powershell
Remove-Item 'D:\projects\RoseMaj\.tmp' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'D:\projects\.tmp' -Recurse -Force -ErrorAction SilentlyContinue
```

### ⚠️ 删除时的安全铁律

**永远不要**对下面这两个路径执行 `-Recurse -Force`，它们是你项目的根：

```text
D:\projects
D:\projects\RoseMaj
```

只删**具体子路径**，并且路径一律用单引号包死。宁可多敲几个字，也别把项目删了
（代码在 GitHub 上丢不了，但 `.venv` 得重建，麻烦）。

---

## 3. 安装后端依赖

```powershell
cd D:\projects\RoseMaj

.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

要装的就三个直接依赖：

```text
fastapi>=0.110
uvicorn[standard]>=0.27
websockets>=12
```

**成功的标志**是最后一行：

```text
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0
fastapi-0.142.1 h11-0.16.0 httptools-0.8.0 idna-3.20 opentelemetry-api-1.45.0 pydantic-2.13.5
pydantic-core-2.46.5 python-dotenv-1.2.3 pyyaml-6.0.3 starlette-1.7.0 typing-extensions-4.16.0
typing-inspection-0.4.4 uvicorn-0.54.0 watchfiles-1.3.0 websockets-17.1
```

只要出现 `Successfully installed` 就是**装完了、没报错**，哪怕光标就停在这一行——
那就是最后一行，后面直接回到提示符。

### 如果清华源也慢 / 失败

换阿里云镜像：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

或者走你自己的代理：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt --proxy http://127.0.0.1:7897
```

---

## 4. 验证依赖装好了

```powershell
.\.venv\Scripts\python.exe -c "import fastapi, uvicorn, websockets; print('fastapi', fastapi.__version__); print('uvicorn', uvicorn.__version__); print('websockets', websockets.__version__)"
```

**本机已验证的实际输出**：

```text
fastapi 0.142.1
uvicorn 0.54.0
websockets 17.1
```

再查一遍依赖之间有没有冲突（无冲突时的输出是 `No broken requirements found.`）：

```powershell
.\.venv\Scripts\python.exe -m pip check
```

---

## 5. 跑一遍测试套件

这一步不需要任何第三方依赖，纯粹验证规则核心没坏：

```powershell
cd D:\projects\RoseMaj
.\.venv\Scripts\python.exe -m unittest discover -v
```

**本机已验证的实际输出**结尾：

```text
----------------------------------------------------------------------
Ran 19 tests in 0.011s

OK
```

`Ran 19 tests` + `OK` 就说明规则核心、CLI、GUI、后端逻辑全部正常。

---

## 6. 运行游戏（四种方式）

### 6.1 命令行版（最快，不用装任何东西）

```powershell
cd D:\projects\RoseMaj
.\.venv\Scripts\python.exe -m roselia_mahjong
```

指定人数和随机种子：

```powershell
.\.venv\Scripts\python.exe -m roselia_mahjong --players 4 --seed 42
```

全 AI 自动跑一局，适合快速验证流程：

```powershell
.\.venv\Scripts\python.exe -m roselia_mahjong --players 2 --ai-only --seed 7
```

### 6.2 桌面图形界面（Tkinter）

```powershell
cd D:\projects\RoseMaj
.\.venv\Scripts\python.exe -m roselia_mahjong.gui
```

也可以直接双击 `RoseliaMahjong_GUI.pyw`（但见第 7 节，那个文件依赖 `python` 命令，建议先修）。

### 6.3 网页联机版（**需要先完成第 3 步**）

```powershell
cd D:\projects\RoseMaj
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

看到这样的输出就是成功了：

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process ...
```

然后浏览器打开：

```text
http://127.0.0.1:8000
```

玩法：填昵称 → 点 **AI Mode** 立刻和 3 个 AI 打一局；想联机就一个人
**Create Room**，另一个人（或另开一个浏览器窗口）用房间号 **Join Room**，
两人都点 **Ready** 自动开局。

### 6.4 一键启动脚本

修好第 7 节的 `.bat` 后，直接双击：

- `RoseliaMahjong_GUI.bat` — 打开桌面版
- `run_online_server.bat` — 启动网页版服务器

---

## 7. 修复 `.bat` 启动脚本（推荐做）

现在这两个文件长这样：

```bat
@echo off
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "F:\anaconda3\python.exe" set "PYTHON_EXE=F:\anaconda3\python.exe"

"%PYTHON_EXE%" -m roselia_mahjong.gui
if errorlevel 1 pause
```

问题：`if exist` 判断的 `F:\` 在本机不存在，于是 `PYTHON_EXE` 保持 `python`
→ 用的是 Anaconda 3.7 → 项目跑不起来。

**改法**：把中间两行换成使用项目自带的虚拟环境。

`RoseliaMahjong_GUI.bat` 改成：

```bat
@echo off
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" -m roselia_mahjong.gui
if errorlevel 1 pause
```

`run_online_server.bat` 改成：

```bat
@echo off
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=py -3.12"

%PYTHON_EXE% -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
pause
```

> 用 `%~dp0` 的意思是「本 bat 文件所在目录」，这样项目挪到哪个盘都能用，
> 不会像原来那样写死 `F:\`。

---

## 8. 常见问题

### `git status` 刷出一堆 `could not open directory 'pip-xxxx/' ... Permission denied`

pip 中断留下的空壳目录，见第 2 节，用管道写法删掉即可。

这些目录**都是空的**，而 git 不跟踪空目录，所以它们**不会**被 `git add` 提交上去，
`commit` 和 `push` 也不受影响——纯粹是警告刷屏。放心。

### `Activate.ps1 : 无法加载文件，因为在此系统上禁止运行脚本`

PowerShell 默认禁止执行脚本。两条路：

**路线 A（推荐）**：不激活，直接用完整路径 `.\.venv\Scripts\python.exe`，就是本教程的写法。

**路线 B**：放开当前用户的执行策略（只影响你自己，不需要管理员）：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

之后就可以用激活方式了，激活后命令能短一些：

```powershell
cd D:\projects\RoseMaj
.\.venv\Scripts\Activate.ps1
python -m roselia_mahjong
deactivate
```

### 提示 `No module named fastapi` / `No module named uvicorn`

依赖没装上，回到第 3 步。也可以先确认你在用哪个 Python：

```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
```

必须输出 `D:\projects\RoseMaj\.venv\Scripts\python.exe`。如果输出的是
`Anaconda3\python.exe`，说明你没走虚拟环境。

### `Fatal error in launcher` 或 pip 报奇怪的编码错

用 `python -m pip` 而不是直接敲 `pip`。本教程所有命令都已经是这个写法。

### 端口 8000 被占用

换一个端口，比如 8010：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8010
```

然后浏览器开 `http://127.0.0.1:8010`。

### pip 下载卡住不动

先 `Ctrl + C` 中断，然后：

1. 清理第 2 节说的 `pip-*` 空壳目录
2. 确认代理是否在跑（`127.0.0.1:7897`）
3. 换成清华源（第 3 节），或显式指定代理

### 误删了整个项目目录

代码在 GitHub 上，丢不了：

```powershell
cd D:\projects
git clone git@github.com:mochihearn-hash/RoseMaj.git
cd RoseMaj
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 注意：`.venv/` 在 `.gitignore` 里，不是仓库内容，**每次重新 clone 都要重建**。
> SSH 密钥和 git 全局配置在 `C:\Users\wangy\` 下，不受影响，不用重配。

---

## 9. 从头重建虚拟环境（万一 `.venv` 坏了）

注意：**必须用 `py -3.12`，不能用裸 `python`**，否则会建出一个 3.7 的环境。

```powershell
cd D:\projects\RoseMaj
Remove-Item .venv -Recurse -Force

py -3.12 -m venv .venv

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

确认版本：

```powershell
.\.venv\Scripts\python.exe --version
```

必须输出 `Python 3.12.x`。

---

## 10. 一页速查

```powershell
# 进项目
cd D:\projects\RoseMaj

# 装依赖（只需一次）
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 清 pip 空壳目录
Get-ChildItem -Directory -Filter 'pip-*' | Remove-Item -Recurse -Force

# 跑测试
.\.venv\Scripts\python.exe -m unittest discover -v

# 命令行版
.\.venv\Scripts\python.exe -m roselia_mahjong --players 4 --seed 42

# 桌面图形版
.\.venv\Scripts\python.exe -m roselia_mahjong.gui

# 网页联机版 → http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# 提交推送
git add .
git commit -m "说明"
git push
```
