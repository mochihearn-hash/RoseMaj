# Roselia Mahjong Prototype

A command-line Python prototype for a Roselia-themed lightweight riichi-like
card game.

## ReseMaj_Online 全栈网页版本

`ReseMaj_Online` 是当前项目的在线网页 MVP。它保留原有 Python 规则核心，并新增：

- `backend/`：FastAPI + WebSocket 后端
- `frontend/`：原生 HTML/CSS/JavaScript 前端
- 内存房间管理，不需要数据库
- 后端权威执行洗牌、发牌、摸牌、弃牌、立直、胡牌、AI 行动
- 浏览器只负责展示状态和发送操作请求

### 全栈项目结构

```text
backend/
  main.py          # FastAPI 入口，WebSocket 和静态前端服务
  models.py        # 玩家、房间、卡牌序列化模型
  game_logic.py    # 在线游戏状态机和规则校验
  room_manager.py  # 房间创建、加入、Ready、广播、AI 推进
  ai_player.py     # AI 简单策略
  requirements.txt

frontend/
  index.html
  style.css
  app.js
```

### 安装后端依赖

```powershell
cd F:\RoseMaj
F:\anaconda3\python.exe -m pip install -r backend\requirements.txt
```

如果你的系统 `python` 已正确配置，也可以使用：

```powershell
python -m pip install -r backend\requirements.txt
```

### 启动在线网页游戏

```powershell
cd F:\RoseMaj
F:\anaconda3\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

然后在浏览器打开：

```text
http://127.0.0.1:8000
```

Windows 下也可以双击：

```text
run_online_server.bat
```

### 在线玩法

首页支持：

- 输入昵称
- Create Room 创建房间
- Join Room 加入房间
- AI Mode 创建 AI 对战房间并立即开始

等待房间：

- 显示房间号
- 显示玩家列表
- 玩家点击 Ready / Cancel Ready
- 2 到 4 人且全员 Ready 后自动开始
- 游戏开始后不可加入新玩家

游戏页：

- 显示自己的手牌
- 显示庄家和当前玩家
- 显示牌堆剩余牌数
- 显示所有玩家牌河
- 显示玩家立直状态
- 摸牌由后端自动执行，不需要 Draw 按钮
- 提供 Discard、Riichi、Tsumo、Ron 按钮
- 点击选择手牌，双击手牌可普通弃牌
- AI 模式结束后，页面中央显示“新游戏”
- 多人模式结束后，所有玩家可重新 Ready；房主在全员 Ready 后点击“重新开始”

### WebSocket 事件

前端发送：

- `create_room`
- `join_room`
- `toggle_ready`
- `start_ai_game`
- `discard_tile`
- `declare_riichi`
- `claim_tsumo`
- `claim_ron`
- `pass_ron`
- `restart_game`

后端广播：

- `room_created`
- `player_joined`
- `player_ready_changed`
- `game_started`
- `game_state_updated`
- `player_drawn`
- `player_discarded`
- `riichi_declared`
- `player_won`
- `game_draw`
- `error`

`pass_ron` 是 MVP 中用于让玩家放弃荣和机会并继续游戏的辅助事件。
摸牌在当前版本中由服务端自动执行，旧的 `draw_tile` 后端事件仍保留为兼容入口，前端不再使用。

## 中文介绍

这是一个以 BanG Dream! 中 Roselia 为主题的轻量级类立直麻将卡牌游戏原型。
当前版本使用 Python 3 编写，先实现命令行玩法，不包含 GUI、联网、复杂计分或番型系统。

项目目标是先做出一个可以运行、可以测试、方便扩展的最小版本。核心规则、玩家状态、
AI 策略和命令行交互被拆分到不同模块中，后续可以继续扩展 GUI、联网对战、AI 策略、
计分系统或更多 Roselia 主题内容。

### 玩法概要

- 支持 2 到 4 名玩家
- 默认 1 名人类玩家，其余为简单 AI
- 每名玩家初始 4 张手牌
- 轮到玩家时先摸 1 张
- 每局开始时，在所有参与角色中随机选择 1 名庄家
- 庄家先行动，之后按座位顺序轮流行动
- 若已经立直且摸牌后组成胡牌，则可以自摸
- 若尚未立直，摸牌后若存在一张可打出的牌，使剩余 4 张处于听牌状态，则可以宣言立直
- 立直顺序为：摸牌、宣言立直、打出立直宣言牌
- 若不能胡牌，必须弃 1 张牌，手牌回到 4 张
- 其他已经立直的玩家可以对弃牌荣和
- 本游戏必须先立直才能胡牌，不允许默听胡牌

### 牌组设定

- 普通牌：5 名角色 x 4 种颜色 x 每种 4 张，共 80 张
- 声优牌：每名角色对应 1 张，共 5 张
- 总牌数：85 张
- 声优牌只能替代对应角色，但可以视为该角色的任意颜色

### 胡牌条件

5 张牌满足以下任意一种即为胡牌：

- Same Character：5 张牌都可以视为同一名角色
- Same Color：5 张牌都可以视为同一种颜色
- Roselia Complete：5 张牌刚好包含 Yukina、Sayo、Lisa、Ako、Rinko 五名不同角色

## Run the game

```powershell
python -m roselia_mahjong
```

Useful options:

```powershell
python -m roselia_mahjong --players 4 --seed 42
python -m roselia_mahjong --players 2 --ai-only --seed 7
```

## 中文运行方式

### 启动图形界面

在项目根目录中双击下面任意一个文件：

- `RoseliaMahjong_GUI.pyw`：推荐，直接打开图形界面
- `RoseliaMahjong_GUI.bat`：备用，会优先使用 `F:\anaconda3\python.exe`

也可以在命令行中启动 GUI：

```powershell
cd F:\RoseMaj
python -m roselia_mahjong.gui
```

GUI 当前支持：

- 查看自己的手牌
- 查看每名玩家的牌河
- 查看牌堆剩余牌数
- 使用“立直”“跳过”“胡牌”按钮
- 双击手牌中的牌进行出牌
- AI 玩家自动行动

### 启动命令行版本

启动默认命令行游戏：

```powershell
python -m roselia_mahjong
```

指定玩家数和随机种子：

```powershell
python -m roselia_mahjong --players 4 --seed 42
```

只让 AI 自动进行一局，适合快速检查游戏流程：

```powershell
python -m roselia_mahjong --players 2 --ai-only --seed 7
```

### PyCharm 运行方式

推荐在 PyCharm 中使用模块方式运行：

- Working directory：项目根目录 `F:\RoseMaj`
- Module name：`roselia_mahjong`
- Interpreter：你的 Python 3 解释器，例如 `F:\anaconda3\python.exe`

也可以直接运行 `F:\RoseMaj\roselia_mahjong\__main__.py`。当前入口文件已经兼容这种方式。

## Run tests

```powershell
python -m unittest discover
```

## 中文测试方式

规则核心、CLI、Tkinter GUI 和后端核心测试可以直接用标准库运行。在线服务器需要先安装
`backend/requirements.txt` 中的 FastAPI 依赖。运行测试：

```powershell
python -m unittest discover -v
```

当前测试覆盖：

- 胡牌判定
- 听牌判定
- 立直判定
- 自摸
- 荣和
- 房间创建
- 房间加入
- Ready 自动开局
- AI 模式创建
- 房间 WebSocket 广播消息结构

安装 FastAPI 依赖后，可用多个浏览器窗口打开 `http://127.0.0.1:8000` 手动验证 WebSocket 联机流程。

## Project layout

```text
roselia_mahjong/
  cards.py      # Card model and Roselia constants
  deck.py       # Deck creation, shuffle, draw
  rules.py      # Winning hand and tenpai checks
  player.py     # Player state
  game.py       # Core game state and legal actions
  ai.py         # Simple AI policy
  gui.py        # Tkinter desktop GUI
  cli.py        # Command-line interaction
  __main__.py   # python -m entry point
backend/
  main.py
  models.py
  game_logic.py
  room_manager.py
  ai_player.py
frontend/
  index.html
  style.css
  app.js
tests/
  test_rules.py
  test_game.py
```

## Current prototype scope

- 2 to 4 players
- One human player by default, remaining seats are simple AI players
- Normal cards: 5 characters x 4 colors x 4 copies
- Voice actor cards: one per character
- Riichi is required before Tsumo or Ron
- Riichi is declared after drawing, then the declaration discard locks the remaining 4-card hand
- Later non-winning draws after riichi are discarded
- Simple Tkinter GUI is included
- No chi, pon, kan, yaku, complex scoring, or networking yet

## 当前原型范围

- 支持 2 到 4 名玩家
- 默认 1 名人类玩家，其余座位为简单 AI
- 实现普通牌、声优牌和完整牌堆
- 实现洗牌、发牌、摸牌、弃牌
- 实现听牌、立直、自摸、荣和
- 实现三种胡牌条件
- 立直改为摸牌后宣言，再打出立直宣言牌
- 立直宣言牌打出后锁定剩余 4 张手牌结构，后续非胡牌摸牌必须直接弃掉
- 已提供简约 Tkinter GUI
- 暂不包含吃、碰、杠、番型、复杂计分或联网
