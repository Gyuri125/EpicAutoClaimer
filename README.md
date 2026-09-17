# 🎮 EpicAutoClaimer

A lightweight, multi-account background automation tool designed to claim weekly and holiday free games from the Epic Games Store without manual hassle.

[![GitHub license](https://img.shields.io/github/license/Gyuri125/EpicAutoClaimer)](https://github.com/Gyuri125/EpicAutoClaimer/blob/main/LICENSE)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Playwright](https://img.shields.io/badge/engine-Playwright-orange)

---

## ✨ Features

* **Multi-Account Support:** Switch between persistent browser sessions without logging in repeatedly.
* **Smart Scheduler:** 
  * Checks automatically every Thursday evening (CET) for new weekly titles.
  * **Holiday Mode:** Switches to daily checks during Christmas daily giveaway sprints (Dec 15 – Jan 5).
* **SQLite Tracking:** Keeps a local history in `epic_bot.db` to avoid duplicate checkout flows.
* **System Tray & Toast Notifications:** Runs silently in the background with native Windows notifications.
* **Built-in Account Manager GUI:** Easily initialize profiles and complete manual 2FA once.

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Gyuri125/EpicAutoClaimer.git](https://github.com/Gyuri125/EpicAutoClaimer.git)
   cd EpicAutoClaimer