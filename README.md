<div align="center">

# EpicAutoClaimer

**Automated Multi-Account Promotion Claim Daemon**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Engine-Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![GraphQL](https://img.shields.io/badge/API-GraphQL-E10098?style=for-the-badge&logo=graphql&logoColor=white)](https://graphql.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-222222?style=for-the-badge)](LICENSE)

<br />

```
[ Epic Store GraphQL ] ──→ [ Scheduler Engine ] ──→ [ SQLite Ledger ]
                                  │
                                  ▼
                     [ Anti-Bot Macro/Micro Jitter ]
                                  │
                                  ▼
                   [ Isolated Chrome / Playwright ]
                                  │
                                  ▼
                   [ Desktop Toast / Tray Service ]
```

</div>

---

## Overview

EpicAutoClaimer is an open-source background automation daemon built to monitor, queue, and claim weekly and promotional giveaway titles from the Epic Games Store without manual user interaction.

It isolates user sessions using dedicated persistent browser profiles, allowing multiple accounts to be managed independently without session crossover, plain-text credential storage, or recurring 2FA prompts. Integrated behavioral randomization and native browser handoffs ensure operations blend seamlessly with organic user activity.

---

## Architectural Workflow

```text
+-------------------------------------------------------------------------+
|                              SCHEDULER                                  |
|   - Standard: Thursday intervals (17:00+ CET)                           |
|   - Holiday Mode: 24h daily polling (Dec 15 - Jan 05)                   |
|   - Macro-Jitter: Random 10-90 min hold on drop detection               |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                       EPIC STORE GRAPHQL CLIENT                         |
|   - Direct query to [store.epicgames.com/graphql](https://store.epicgames.com/graphql)                         |
|   - Filters category: "freegames" with discountPercentage == 0          |
|   - Headless browser fallback if network inspection triggers            |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                        SQLITE IDEMPOTENCY LEDGER                        |
|   - Verifies (account_name, game_slug) composite record                 |
|   - If record exists: SKIP -> Eliminates redundant store operations     |
|   - If record missing: PROCEED to staged account queue                  |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                       MULTI-ACCOUNT QUEUE RUNNER                        |
|   - Shuffles profile execution order                                    |
|   - Enforces sequential processing (one browser instance at a time)     |
|   - Inserts 2-6 min cooldown between account transitions                |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                     AUTOMATION ENGINE (Playwright)                      |
|   - Loads isolated persistent session: ./profiles/{account}             |
|   - Strips automation flags (navigator.webdriver masked)                |
|   - Employs micro-jitter (human delay intervals on clicks/navigation)   |
|   - Traverses age verification gateways & checkout iframes              |
|   - Confirms order & commits transaction to database                    |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                           NOTIFICATION LAYER                            |
|   - Dispatches native Windows desktop toast notifications               |
|   - Updates system tray icon status                                     |
+-------------------------------------------------------------------------+
```

---

## Key Capabilities

* **Multi-Account Profile Isolation**  
  Each managed account operates within an independent sandbox directory (`./profiles/{account}`). Authentication cookies, tokens, and storage state remain strictly isolated.

* **Heuristic Anti-Detection & Behavioral Jitter**  
  Eliminates machine-like timing patterns using multi-level randomization:
  * **Macro-Jitter:** Pauses execution randomly between 10 and 90 minutes after a new promotion appears.
  * **Queue Shuffling:** Randomizes account processing order on every run.
  * **Inter-Account Cooldowns:** Introduces 2 to 6 minute pauses between accounts to simulate organic user handoffs.
  * **Micro-Jitter:** Simulates human reaction times (2.0s to 8.0s delays) across button interactions and page transitions.

* **Native Chrome Authentication Handoff**  
  Initial logins and two-factor authentication (2FA) execute via native system Google Chrome processes without automated test flags (`--no-sandbox` omitted), preventing Arkose Labs puzzle lockouts.

* **Direct GraphQL Catalog Integration**  
  Interfaces directly with Epic's official GraphQL backend for fast, accurate promotion detection, backed by a headless browser scraping fallback.

* **Idempotent Claim Tracking**  
  Every successful transaction is recorded in an embedded SQLite database (`epic_bot.db`). The engine cross-references this index before launching browser instances, avoiding redundant storefront operations.

* **Adaptive Seasonal Scheduling**  
  Automatically switches between standard weekly runs (every Thursday evening) and holiday giveaway marathons (December 15 through January 05).

---

## Multi-Monitor Compatibility

The client is optimized for multi-display workstations to eliminate disruption during regular workflows:

| Attribute | Implementation Detail |
|---|---|
| **Window State** | Scheduled claims run in managed browser contexts without stealing keyboard or window focus. |
| **GUI Routing** | Configuration windows and manual login sessions anchor dynamically to the active display workspace. |
| **Notifications** | Alerts are routed through native OS notification channels, adhering to system Focus Assist and full-screen gaming rules. |

---

## Global & Contextual Keybindings

| Shortcut | Scope | Function |
|---|---|---|
| `Ctrl + Alt + C` | Global | Trigger immediate catalog poll and claim execution |
| `Ctrl + Alt + M` | Global | Bring Account Management window to foreground |
| `Enter` | GUI Window | Submit account creation / Confirm active prompt |
| `Escape` | GUI Window | Minimize active configuration window back to tray |

---

## Repository Structure

```text
EpicAutoClaimer/
│
├── profiles/                [Untracked] Isolated browser sessions & tokens
│   ├── account_alpha/       Local cache for User Alpha
│   └── account_beta/        Local cache for User Beta
│
├── src/
│   ├── __init__.py
│   ├── database.py          SQLite schema initialization and ledger queries
│   ├── epic_api.py          GraphQL client, query parser, and scraping fallback
│   ├── claimer.py           Playwright automation routines and native Chrome login
│   ├── scheduler.py         Date logic (Thursday drops vs. daily Holiday sprints)
│   └── gui.py               Tkinter account manager interface
│
├── main.py                  System tray entrypoint and background worker thread
├── requirements.txt         Python package dependencies
├── .gitignore               Git security rules (excludes profiles, databases, logs)
├── LICENSE                  MIT License terms
└── README.md                Technical documentation
```

---

## Installation & Setup

### Prerequisites

* Python 3.10 or higher
* Google Chrome installed (recommended for native 2FA login handoff)
* Git CLI

### 1. Repository Setup

```bash
git clone [https://github.com/Gyuri125/EpicAutoClaimer.git](https://github.com/Gyuri125/EpicAutoClaimer.git)
cd EpicAutoClaimer
```

### 2. Environment Configuration

```bash
python -m venv .venv

# Windows (Command Prompt / PowerShell):
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate
```

### 3. Dependency Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Launch Application

```bash
python main.py