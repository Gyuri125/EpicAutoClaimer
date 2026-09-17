<div align="center">

# EpicAutoClaimer

**Automated Multi-Account Promotion Claim Daemon**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Engine-Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-222222?style=for-the-badge)](LICENSE)

<br />

```
[ Epic Store API ] ──→ [ Scheduler Engine ] ──→ [ SQLite Ledger ]
                              │
                              ▼
                 [ Headless Playwright Context ]
                              │
                              ▼
                 [ Desktop Toast / Tray Service ]
```

</div>

---

## Overview

EpicAutoClaimer is an open-source background automation daemon built to monitor, queue, and claim weekly and promotional giveaway titles from the Epic Games Store without manual user interaction. 

It isolates user sessions using dedicated persistent browser profiles, allowing multiple accounts to be managed independently without session crossover, password exposure, or recurring 2FA prompts.

---

## Architectural Workflow

```text
+-------------------------------------------------------------------------+
|                              SCHEDULER                                  |
|   - Standard: Thursday intervals (17:00-20:00 CET)                      |
|   - Holiday Mode: 24h daily polling (Dec 15 - Jan 05)                   |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                          EPIC CATALOG PARSER                            |
|   - Queries Akamai store endpoint (HTTP GET)                            |
|   - Filters discount percentage == 0                                    |
|   - Resolves product slugs & store URLs                                 |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                        SQLITE IDEMPOTENCY LEDGER                        |
|   - Checks (account_name, game_slug) composite key                      |
|   - If record exists: SKIP → Prevents checkout loops                    |
|   - If record missing: PROCEED to Claim Flow                            |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                        AUTOMATION ENGINE (Playwright)                   |
|   - Loads isolated user session: ./profiles/{account}                   |
|   - Traverses age verification gateways                                 |
|   - Bypasses purchase iframe boundaries                                 |
|   - Confirms order & writes success entry to database                   |
+------------------------------------+------------------------------------+
                                     |
                                     ▼
+-------------------------------------------------------------------------+
|                           NOTIFICATION LAYER                            |
|   - Native Windows notification dispatch                                |
|   - System tray icon status update                                      |
+-------------------------------------------------------------------------+
```

---

## Key Capabilities

* **Multi-Account Profile Isolation**  
  Each managed account operates within its own sandbox directory. Authentication cookies, local storage state, and device fingerprints remain isolated.

* **Non-Interactive Execution**  
  Automated claiming runs entirely without user interaction. Scheduled background sweeps check store promotions periodically and claim eligible items automatically.

* **Idempotent Claim Tracking**  
  Every confirmed claim is written to an internal SQLite ledger (`epic_bot.db`). The bot cross-references this index before launching browser instances, avoiding redundant load operations.

* **Adaptive Seasonal Scheduling**  
  The scheduler dynamically switches between standard weekly operations (every Thursday evening) and seasonal daily giveaway sprints (December 15 through January 05).

* **Zero Plain-Text Credentials**  
  No account passwords or private keys are stored on disk. Accounts are initialized via manual login through a localized browser window, storing only authenticated session tokens.

---

## Multi-Monitor Compatibility

The client is optimized for multi-display workstations to eliminate disruption during regular workflows:

| Attribute | Implementation Detail |
|---|---|
| **Window State** | Routine tasks run via background browser processes without stealing window or keyboard focus. |
| **GUI Routing** | Configuration windows and manual login sessions dynamically snap to the active display workspace. |
| **Notifications** | Alerts are routed through native OS notification channels, adhering to system focus assist and full-screen gaming rules. |

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
├── profiles/                [Untracked] Local browser cache & session cookies
│   ├── account_alpha/       Profile data for User Alpha
│   └── account_beta/        Profile data for User Beta
│
├── src/
│   ├── __init__.py
│   ├── database.py          SQLite schema initialization and ledger operations
│   ├── epic_api.py          Akamai REST endpoint client and payload parser
│   ├── claimer.py           Playwright automation routines and iframe handlers
│   ├── scheduler.py         Time logic (Thursday weekly vs. daily Holiday mode)
│   └── gui.py               Tkinter account profile and session manager
│
├── main.py                  System tray entrypoint and background worker thread
├── requirements.txt         Python package dependencies
├── .gitignore               Git security exclusion list (ignores db, profiles)
├── LICENSE                  MIT License terms
└── README.md                Technical documentation
```

---

## Installation & Setup

### Prerequisites

* Python 3.10 or higher
* Git CLI

### 1. Repository Setup

```bash
git clone [https://github.com/Gyuri125/EpicAutoClaimer.git](https://github.com/Gyuri125/EpicAutoClaimer.git)
cd EpicAutoClaimer
```

### 2. Environment Configuration

```bash
python -m venv venv

# Windows (cmd/PowerShell):
venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate
```

### 3. Dependency Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Launch Application

```bash
python main.py
```

---

## Account Initialization

> **Important:** Account initialization requires a one-time manual sign-in to bypass Cloudflare and verify two-factor authentication (2FA).

1. Execute `python main.py`. An icon will populate within your system tray.
2. Right-click the tray icon and select **Fiókok kezelése (Manage Accounts)**.
3. Input an identifier into the field (e.g., `main_account`) and select **Hozzáadás (Add)**.
4. Highlight the newly added profile and select **Belépés / 2FA beállítása**.
5. Log into Epic Games via the opened browser instance, ensure **Remember Me** is checked, and complete any 2FA/Captcha requirements.
6. Close the browser window once the Epic Store home page loads. The profile is now cached permanently in the local `./profiles/` directory.

---

## Technical Stack

* **Language:** Python 3.10+
* **Browser Driver:** [Playwright](https://playwright.dev/python/) (Chromium)
* **API Client:** [Requests](https://requests.readthedocs.io/)
* **Tray Integration:** [Pystray](https://pystray.readthedocs.io/)
* **Storage Engine:** SQLite3 (Native)
* **Image Processing:** [Pillow](https://python-pillow.org/)
* **Interface:** Tkinter (Native)

---

## Legal & Compliance Notice

This utility is developed strictly for educational and automation research purposes. Automating account interactions with storefronts may conflict with Epic Games' End User License Agreement (EULA) and Terms of Service. Use at your own discretion.

---

## License

Distributed under the MIT License. Refer to the [LICENSE](LICENSE) file for complete terms.