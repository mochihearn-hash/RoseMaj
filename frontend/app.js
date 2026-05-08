const state = {
  socket: null,
  room: null,
  selectedCardIndex: null,
};

const els = {
  connectionStatus: document.getElementById("connectionStatus"),
  homeView: document.getElementById("homeView"),
  roomView: document.getElementById("roomView"),
  gameView: document.getElementById("gameView"),
  nicknameInput: document.getElementById("nicknameInput"),
  roomCodeInput: document.getElementById("roomCodeInput"),
  aiCountInput: document.getElementById("aiCountInput"),
  createRoomButton: document.getElementById("createRoomButton"),
  joinRoomButton: document.getElementById("joinRoomButton"),
  aiModeButton: document.getElementById("aiModeButton"),
  roomCodeLabel: document.getElementById("roomCodeLabel"),
  playerList: document.getElementById("playerList"),
  readyButton: document.getElementById("readyButton"),
  gameRoomCode: document.getElementById("gameRoomCode"),
  turnLabel: document.getElementById("turnLabel"),
  deckRemaining: document.getElementById("deckRemaining"),
  endGamePanel: document.getElementById("endGamePanel"),
  endSummary: document.getElementById("endSummary"),
  restartStatus: document.getElementById("restartStatus"),
  endReadyButton: document.getElementById("endReadyButton"),
  restartGameButton: document.getElementById("restartGameButton"),
  newAiGameButton: document.getElementById("newAiGameButton"),
  gamePlayers: document.getElementById("gamePlayers"),
  discardArea: document.getElementById("discardArea"),
  handArea: document.getElementById("handArea"),
  handHint: document.getElementById("handHint"),
  discardButton: document.getElementById("discardButton"),
  riichiButton: document.getElementById("riichiButton"),
  tsumoButton: document.getElementById("tsumoButton"),
  ronButton: document.getElementById("ronButton"),
  passRonButton: document.getElementById("passRonButton"),
  messageLog: document.getElementById("messageLog"),
};

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  state.socket = socket;

  socket.addEventListener("open", () => {
    els.connectionStatus.textContent = "Connected";
    els.connectionStatus.className = "status-pill connected";
    log("已连接服务器。");
  });

  socket.addEventListener("close", () => {
    els.connectionStatus.textContent = "Disconnected";
    els.connectionStatus.className = "status-pill error";
    log("连接已断开，请刷新页面重连。");
  });

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    handleMessage(message);
  });
}

function send(type, payload = {}) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    log("WebSocket 尚未连接。");
    return;
  }
  state.socket.send(JSON.stringify({ type, payload }));
}

function handleMessage(message) {
  const payload = message.payload || {};
  if (message.type === "error") {
    log(`错误：${payload.message}`);
    return;
  }

  if (payload.state) {
    state.room = payload.state;
    const handLength = state.room.game?.you?.hand?.length ?? 0;
    if (state.selectedCardIndex !== null && state.selectedCardIndex >= handLength) {
      state.selectedCardIndex = null;
    }
    render();
  }

  if (message.type === "room_created") {
    log(`房间已创建：${payload.room_code}`);
  } else if (message.type === "player_joined") {
    log("有玩家加入房间。");
  } else if (message.type === "player_ready_changed") {
    log("准备状态已更新。");
  } else if (message.type === "game_started") {
    log("游戏开始。");
  } else if (message.type === "player_drawn") {
    log(`${playerName(payload.player_id)} 摸牌。`);
  } else if (message.type === "player_discarded") {
    log(`${playerName(payload.player_id)} 弃牌：${payload.card?.label || ""}`);
  } else if (message.type === "riichi_declared") {
    log(`${playerName(payload.player_id)} 立直，打出：${payload.card?.label || ""}`);
  } else if (message.type === "player_won") {
    const winner = payload.winner || payload.state?.game?.winner;
    log(formatWinner(winner));
  } else if (message.type === "game_draw") {
    log(`流局：${payload.reason || "牌堆耗尽"}`);
  }
}

function render() {
  if (!state.room) {
    showOnly("home");
    return;
  }

  if (state.room.status === "waiting") {
    showOnly("room");
    renderRoom();
    return;
  }

  showOnly("game");
  renderGame();
}

function showOnly(view) {
  els.homeView.classList.toggle("hidden", view !== "home");
  els.roomView.classList.toggle("hidden", view !== "room");
  els.gameView.classList.toggle("hidden", view !== "game");
}

function renderRoom() {
  els.roomCodeLabel.textContent = state.room.room_code;
  els.playerList.innerHTML = "";
  for (const player of state.room.players) {
    const row = document.createElement("div");
    row.className = "player-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(player.nickname)}</strong>
        ${player.is_ai ? '<span class="tag">AI</span>' : ""}
      </div>
      <span class="tag ${player.ready ? "ready" : "not-ready"}">
        ${player.ready ? "Ready" : "Not Ready"}
      </span>
    `;
    els.playerList.appendChild(row);
  }

  const me = currentPlayer();
  els.readyButton.textContent = me?.ready ? "Cancel Ready" : "Ready";
}

function renderGame() {
  const game = state.room.game;
  if (!game) return;

  const actions = game.available_actions || {};
  els.gameRoomCode.textContent = state.room.room_code;
  els.turnLabel.textContent =
    `庄家：${game.dealer_nickname} | 当前玩家：${game.current_player_nickname} | 阶段：${phaseText(game.phase)}`;
  els.deckRemaining.textContent = game.deck_remaining;

  renderGamePlayers(game);
  renderDiscards(game);
  renderHand(game);
  renderEndGamePanel(game);

  const riichiIndexes = new Set((game.riichi_options || []).map((item) => item.index));
  const selectedCanRiichi =
    state.selectedCardIndex !== null && riichiIndexes.has(state.selectedCardIndex);

  els.discardButton.disabled = !actions.can_discard || state.selectedCardIndex === null;
  els.riichiButton.disabled = !actions.can_riichi || !selectedCanRiichi;
  els.tsumoButton.disabled = !actions.can_tsumo;
  els.ronButton.disabled = !actions.can_ron;
  els.passRonButton.disabled = !actions.can_ron;

  if (actions.can_riichi) {
    const options = game.riichi_options || [];
    const labels = options.map((item) => `${item.index}: ${item.discard.label}`).join(" / ");
    els.handHint.textContent = `可立直弃牌：${labels}`;
  } else if (actions.can_discard) {
    els.handHint.textContent = "点击选择，双击普通出牌";
  } else if (actions.can_ron) {
    els.handHint.textContent = "你可以荣和，点击 Ron 或 Pass Ron";
  } else if (state.room.status === "finished") {
    els.handHint.textContent = "本局已结束";
  } else {
    els.handHint.textContent = "等待其他玩家行动";
  }
}

function renderEndGamePanel(game) {
  const finished = state.room.status === "finished";
  els.endGamePanel.classList.toggle("hidden", !finished);
  if (!finished) {
    return;
  }

  els.endSummary.textContent = formatWinner(game.winner);
  els.restartStatus.innerHTML = "";
  for (const player of state.room.players) {
    const row = document.createElement("div");
    row.innerHTML = `
      <strong>${escapeHtml(player.nickname)}</strong>
      <span class="tag ${player.ready ? "ready" : "not-ready"}">
        ${player.ready ? "Ready" : "Not Ready"}
      </span>
    `;
    els.restartStatus.appendChild(row);
  }

  const isAiRoom = Boolean(state.room.is_ai_room);
  els.newAiGameButton.classList.toggle("hidden", !isAiRoom);
  els.endReadyButton.classList.toggle("hidden", isAiRoom || !state.room.can_toggle_ready);
  els.restartGameButton.classList.toggle("hidden", isAiRoom || !state.room.you?.is_owner);

  const me = currentPlayer();
  els.endReadyButton.textContent = me?.ready ? "Cancel Ready" : "Ready";
  els.restartGameButton.disabled = !state.room.can_restart;
  els.newAiGameButton.disabled = !state.room.can_restart;
}

function renderGamePlayers(game) {
  els.gamePlayers.innerHTML = "";
  for (const player of game.players) {
    const row = document.createElement("div");
    row.className = `player-row ${player.id === game.current_player_id ? "current" : ""}`;
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(player.nickname)}</strong>
        ${player.is_ai ? '<span class="tag">AI</span>' : ""}
        ${player.id === game.dealer_player_id ? '<span class="tag dealer">庄家</span>' : ""}
        ${player.riichi ? '<span class="tag riichi">Riichi</span>' : ""}
      </div>
      <div class="tag">手牌 ${player.hand_count}</div>
    `;
    els.gamePlayers.appendChild(row);
  }
}

function renderDiscards(game) {
  els.discardArea.innerHTML = "";
  for (const player of game.players) {
    const river = document.createElement("div");
    river.className = "river";
    const cards = player.discards.map((card) => cardHtml(card, true)).join("");
    river.innerHTML = `
      <div class="river-title">${escapeHtml(player.nickname)} 的牌河</div>
      <div class="river-cards">${cards || '<span class="tag">暂无弃牌</span>'}</div>
    `;
    els.discardArea.appendChild(river);
  }
}

function renderHand(game) {
  els.handArea.innerHTML = "";
  const hand = game.you?.hand || [];
  for (const [index, card] of hand.entries()) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = cardHtml(card, false);
    const cardEl = wrapper.firstElementChild;
    if (index === state.selectedCardIndex) {
      cardEl.classList.add("selected");
    }
    cardEl.addEventListener("click", () => {
      state.selectedCardIndex = index;
      renderGame();
    });
    cardEl.addEventListener("dblclick", () => {
      if (game.available_actions?.can_discard) {
        send("discard_tile", { card_index: index });
      }
    });
    els.handArea.appendChild(cardEl);
  }
}

function cardHtml(card, small) {
  const colorClass = card.is_voice_actor ? "card-voice" : `card-${String(card.color).toLowerCase()}`;
  const name = card.is_voice_actor ? card.voice_actor : card.character;
  const sub = card.is_voice_actor ? `→ ${card.character}` : card.color;
  return `
    <div class="card ${small ? "small" : ""} ${colorClass}">
      <div class="name">${escapeHtml(name)}</div>
      <div class="sub">${escapeHtml(sub)}</div>
    </div>
  `;
}

function currentPlayer() {
  const id = state.room?.you?.id;
  return state.room?.players?.find((player) => player.id === id);
}

function playerName(playerId) {
  const players = state.room?.game?.players || state.room?.players || [];
  return players.find((player) => player.id === playerId)?.nickname || "玩家";
}

function nickname() {
  return els.nicknameInput.value.trim() || "Guest";
}

function selectedIndex() {
  if (state.selectedCardIndex === null) {
    log("请先选择一张手牌。");
    return null;
  }
  return state.selectedCardIndex;
}

function log(message) {
  const line = document.createElement("div");
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  els.messageLog.appendChild(line);
  els.messageLog.scrollTop = els.messageLog.scrollHeight;
}

function formatWinner(winner) {
  if (!winner) return "游戏结束。";
  const parts = [`${winner.method}: ${winner.winner_nickname} 胜利`];
  if (winner.discarder_nickname) {
    parts.push(`放铳：${winner.discarder_nickname}`);
  }
  if (winner.winning_card) {
    parts.push(`和牌：${winner.winning_card.label}`);
  }
  if (winner.win_types_text) {
    parts.push(`牌型：${winner.win_types_text}`);
  }
  return parts.join("；");
}

function phaseText(phase) {
  return {
    waiting: "等待",
    need_draw: "自动摸牌中",
    after_draw: "摸牌后",
    finished: "结束",
  }[phase] || phase;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

els.createRoomButton.addEventListener("click", () => {
  send("create_room", { nickname: nickname() });
});

els.joinRoomButton.addEventListener("click", () => {
  send("join_room", {
    nickname: nickname(),
    room_code: els.roomCodeInput.value.trim().toUpperCase(),
  });
});

els.aiModeButton.addEventListener("click", () => {
  send("start_ai_game", {
    nickname: nickname(),
    ai_count: Number(els.aiCountInput.value),
  });
});

els.readyButton.addEventListener("click", () => {
  send("toggle_ready");
});

els.discardButton.addEventListener("click", () => {
  const index = selectedIndex();
  if (index !== null) {
    send("discard_tile", { card_index: index });
  }
});

els.riichiButton.addEventListener("click", () => {
  const index = selectedIndex();
  if (index !== null) {
    send("declare_riichi", { card_index: index });
  }
});

els.tsumoButton.addEventListener("click", () => {
  send("claim_tsumo");
});

els.ronButton.addEventListener("click", () => {
  send("claim_ron");
});

els.passRonButton.addEventListener("click", () => {
  send("pass_ron");
});

els.endReadyButton.addEventListener("click", () => {
  send("toggle_ready");
});

els.restartGameButton.addEventListener("click", () => {
  send("restart_game");
});

els.newAiGameButton.addEventListener("click", () => {
  send("restart_game");
});

connect();
