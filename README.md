<div align="center">

# EpicAutoClaimer

**Autonomous Multi-Account Store Promotion Claim Engine & System Tray Daemon**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Automation-Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![GraphQL](https://img.shields.io/badge/API-GraphQL-E10098?style=for-the-badge&logo=graphql&logoColor=white)](https://graphql.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-222222?style=for-the-badge)](LICENSE)

<br />

```
+-------------------------+     +------------------------+     +------------------------+
|  Epic Store GraphQL API | --> |  Autonomous Scheduler  | --> |  SQLite State Ledger   |
+-------------------------+     +-----------+------------+     +------------------------+
                                            |
                                            v
                                +------------------------+
                                │ Heuristic Anti-Detect  │
                                +-----------+------------+
                                            |
                                            v
+-------------------------+     +------------------------+     +------------------------+
| Live GUI & Stream Logs  | <-- | Isolated Chrome (CDP)  | --> | Native Windows Toasts  |
+-------------------------+     +------------------------+     +------------------------+
```

</div>

---

## Overview

EpicAutoClaimer is a background automation daemon engineered to monitor, verify, and claim weekly promotions and holiday giveaways from the Epic Games Store across multiple user accounts.

The engine executes autonomous checkout workflows through persistent browser sessions, eliminating recurring multi-factor authentication (2FA) challenges and removing the need to store plain-text account credentials. By integrating Chrome DevTools Protocol (CDP) attachment, humanized interaction profiles, and automated storefront license introspection, it operates without disrupting active desktop workflows.

---

## Key Advantages

- **Personal Browser Immunity (CDP Isolation):** Connects to dedicated, isolated Google Chrome contexts via debug port `127.0.0.1:9222`. Active personal Chrome windows, extensions, and sessions remain completely untouched.
- **Dual-Layer Anti-Redundancy:**
  - *Embedded Ledger:* SQLite index verifies past claims to prevent unnecessary browser startups and CPU overhead.
  - *Storefront Introspection:* Automatically detects pre-owned licenses (`In Library` status) on the live product page and synchronizes the local database without submitting duplicate orders.
- **Zero Plain-Text Credentials:** Passwords and private keys are never requested or stored. Profiles maintain isolated session cookies and tokens within local sandbox directories (`./profiles/{account}`).
- **Anti-Bot & Challenge Handling:** Employs curved mouse trajectories, variable-speed viewport scrolling, micro-delays, and audible notifications (`winsound.Beep`) if manual Arkose Labs puzzles are presented.
- **Integrated Dashboard & Observability:** Features a Tkinter management console with a live streaming terminal, manual batch-triggering controls, and rolling diagnostic log files (`logs/app.log`).
- **Adaptive Scheduling Engine:** Automatically transitions between standard weekly release sweeps (Thursdays 17:00+ CET) and continuous daily polling cycles during seasonal holiday campaigns (Dec 15 – Jan 05).

---

## Multi-Monitor Operation

EpicAutoClaimer is structured to minimize interruption across multi-display workstations:

| Display Aspect | Implementation Details |
|---|---|
| **Window State** | Background claims run without stealing focus or interrupting active full-screen applications. |
| **Workspace Routing** | Manual authentication windows and dashboard dialogues dynamically open on the active display monitor. |
| **Notification Pipeline** | Dispatches desktop alerts through native Windows toast APIs, adhering to Windows Focus Assist rules. |

---

## Keyboard Shortcuts

| Key Combination | Context | Function |
|---|---|---|
| `Ctrl + Alt + C` | Global | Trigger immediate catalog check and claim routine across all accounts |
| `Ctrl + Alt + M` | Global | Bring Account Management Control Panel to the foreground |
| `Enter` | GUI Interface | Confirm account registration / Submit focused dialogue |
| `Escape` | GUI Interface | Dismiss active dialogue and return focus to system tray |

---

## Tech Stack

- **Runtime:** Python 3.10+
- **Browser Automation:** Playwright (Chromium) attached via Chrome DevTools Protocol (CDP)
- **API Client:** Requests (Akamai Store Endpoints & GraphQL API)
- **Storage Layer:** SQLite3 (Embedded state ledger)
- **Daemon & Tray Interface:** Pystray
- **Graphical Dashboard:** Tkinter & TTK
- **Imaging & Drawing:** Pillow

---

## Repository Structure

```text
EpicAutoClaimer/
│
├── profiles/                [Untracked] Persistent browser state and session tokens
│   ├── User_Alpha/          Sandbox directory for Account 1
│   └── User_Beta/           Sandbox directory for Account 2
│
├── logs/                    [Untracked] Runtime execution and diagnostic logs
│   └── app.log              Persistent rotating application log
│
├── debug_screenshots/       [Untracked] Error and timeout screen captures
│
├── src/
│   ├── __init__.py
│   ├── database.py          SQLite schema, account records, and claim history
│   ├── epic_api.py          GraphQL client and store slug resolver
│   ├── claimer.py           CDP connection, automation sequence, and checkout handler
│   ├── logger.py            Thread-safe logging pipeline (Console, File, GUI)
│   ├── scheduler.py         Weekly interval and holiday mode date calculator
│   └── gui.py               Control dashboard and live terminal window
│
├── main.py                  System tray entry point and background loop
├── requirements.txt         Package dependency manifest
├── .gitignore               Exclusion list for credentials, databases, and logs
├── LICENSE                  MIT License agreement
└── README.md                Technical documentation
```

---

## Installation & Setup

### Prerequisites

- Windows 10 / 11 (64-bit)
- Python 3.10 or higher
- Google Chrome installed in standard system paths
- Git CLI

### 1. Repository Setup

```bash
git clone [https://github.com/Gyuri125/EpicAutoClaimer.git](https://github.com/Gyuri125/EpicAutoClaimer.git)
cd EpicAutoClaimer
```

### 2. Virtual Environment Configuration

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Launch Application

```bash
python main.py
```

---

## Initial Account Authentication

1. Execute `python main.py`. An icon will initialize in the Windows System Tray (notification area).
2. Right-click the tray icon and select **Open Control Panel** (Vezérlőpult megnyitása).
3. Provide an account identifier in the input field and click **Add Account** (Fiók hozzáadása).
4. Highlight the account name in the list and click **Open Browser** (Böngésző megnyitása).
5. A dedicated Chrome instance will launch. Log into the respective Epic Games account, select **Remember Me**, and complete any necessary 2FA or security checks.
6. Close the browser window. Session cookies are permanently retained under `./profiles/{account}`. Repeat this step for additional accounts.

---

## Standalone Executable Build (Optional)

To compile the application into a standalone Windows binary with no command-line window:

```bash
pip install pyinstaller

pyinstaller --noconsole --onefile --name "EpicAutoClaimer" \
  --add-data "src;src" \
  main.py
```

---

## License

This project is licensed under the MIT License. Refer to the [LICENSE](LICENSE) file for complete details.