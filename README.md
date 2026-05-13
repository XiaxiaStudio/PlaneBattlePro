## 🎮 About

**Fei Ji Da Zhan Pro** (Plane Battle Pro) is a classic vertical shoot 'em up (STG) built entirely with Python + Pygame. All sprites are hand-pixeled in code with zero external assets.

| Feature | Details |
|---------|---------|
| 🖼️ Pixel Art | All sprites drawn programmatically |
| ⏱️ Power-ups | Spread / Rapid / Shield, 30s each, max 3 stacks |
| 🔥 Combo System | Kill streak with combo timer bar |
| 👹 Boss Fights | Every 500 points, 3 boss types, multi-phase |
| 💾 Save System | Auto-save high score, export/import support |
| 🖥️ Launcher | C++ auto-dependency installer |
| 🌐 China Mirror | Auto IP detection + mirror acceleration |

## 🎯 Controls

### Main Menu
| Action | Keys |
|--------|------|
| Navigate | `W` `S` / `↑` `↓` |
| Confirm | `Space` / `Enter` |
| Cancel | `ESC` |

### In-Game
| Mode | Move | Shoot |
|------|------|-------|
| 🖱️ Mouse | Mouse movement | Left click |
| ⌨️ Keyboard | `WASD` / Arrows | `Space` |

### Pause Menu (`ESC`)
Resume / Restart / Quit to Menu / Export Save / Import Save

## ⚡ Quick Start

### Option 1: Launcher (Recommended)
1. Download `launcher.exe` + `shoot_game.py`
2. Place them in the same folder
3. Double-click `launcher.exe`

### Option 2: Command Line
```bash
pip install pygame
python shoot_game.py
```

## 🛠️ Tech Stack

| Layer | Tech |
|-------|------|
| Engine | Pygame 2.x |
| Sprites | Code-drawn pixel art |
| Launcher | C++ / Win32 API |
| Sound | Procedural audio (sine wave synthesis) |
| Saves | JSON |

## 🏆 Scoring

| Enemy | Score | Health |
|-------|-------|--------|
| Scout | +10 | 1 HP |
| Fighter | +25 | 2 HP |
| Bomber | +50 | 4 HP |
| Boss | +200~300 | 20~50 HP |
| Combo Bonus | ×(1 + combo/5) | — |

## 📄 License

MIT License. Copyright (c) 2026 **XiaxiaStudioGames (XSGames)**

See [LICENSE.txt](LICENSE.txt)

---

**Made with ❤️ by XiaxiaStudioGames (XSGames)**
