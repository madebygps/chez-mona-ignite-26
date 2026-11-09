# Chez Mona lab launcher spec

Booth: Chez Mona, Microsoft Ignite 2026
Status: all four labs' material built. Launcher and fridge ticket kiosk built in [`launcher/`](launcher/). The full flow (fridge ticket, scan, Fried Chicken in VS Code, quiz, wrap up, receipt) passed on one laptop with a real USB receipt printer; open items are in [To verify before the event](#to-verify-before-the-event).

## Goal

A local web app on each booth laptop for a 5 minute lab:
scan a fridge ticket or choose a lab, read instructions, explore, answer a short quiz, print a receipt with a docs QR code.

## Decisions

| Area | Decision |
|---|---|
| Format | Explore, then quiz, then printed receipt |
| Machines and accounts | Booth provided, shared booth account |
| Launcher hosting | Local web app on each laptop, served on `localhost` |
| Laptop to lab mapping | Any laptop runs any dish, chosen by scanning a ticket or picking a lab on screen |
| Ticket scanning | Laptop webcam, in the browser |
| Ticket QR content | Dish ID only, tickets are reusable |
| Wrong quiz answer | Show a hint, retry until correct |
| Abandoned lab | Idle prompt "Still cooking?", then return to scan screen |

## Lineup

| Dish | Lab | Explore surface | Prepared material |
|---|---|---|---|
| Canvas collaboration omelette (Omelette) | GitHub Copilot app Canvas | GitHub Copilot app | Public guest repo [madebygps/canvas-101](https://github.com/madebygps/canvas-101) with the repository scoped Chez Mona order ticket canvas |
| Copilot SDK fried chicken (Fried Chicken) | Copilot SDK | VS Code with Copilot Chat | Small Python starter in the booth repo, based on the official SDK sample |
| Agentic alphabet soup (Soup) | Agentic Workflows | GitHub.com | Upstream [github-samples/tailspin-toys](https://github.com/github-samples/tailspin-toys) triage workflow file, pinned to a commit |
| Autofix artichoke dip (Dip) | PR review | GitHub.com | Tiny booth owned Chez Mona repo with an "Add menu search" PR that already has code scanning, Copilot Autofix and Copilot code review comments |

## Repositories

Guests never open the booth repo, so its spec, quiz answers and launcher code stay out of reach. Each laptop clones two repos:

| Repo | Who opens it | Contents |
|---|---|---|
| [madebygps/chez-mona-ignite-26](https://github.com/madebygps/chez-mona-ignite-26) (private) | Staff and the launcher | `launcher/`, `copilot-sdk/` Fried Chicken starter, this spec |
| [madebygps/canvas-101](https://github.com/madebygps/canvas-101) (public) | Guests, in the Copilot app | Omelette canvas in `.github/extensions/chez-mona-order-ticket/` and a guest-safe `AGENTS.md` that keeps the agent from editing files |

The Fried Chicken starter needs no repo of its own: the launcher copies it into a temp folder for each guest. Soup and Dip are visited on GitHub.com, so they are not cloned. Soup uses the upstream `tailspin-toys` repo; Dip uses the public booth owned repo `madebygps/chez-mona-dip`.

## Screen flow

1. **Scan or choose.** Webcam view with "Scan your ticket" and a visible **Manually select a lab instead** button. The button opens the four-dish menu without needing a ticket; choosing a dish opens its intro. **Scan a ticket instead** returns to the webcam.
2. **Intro.** The lab name, the dish, then `uses` and "You'll learn" with the `about` points, as on the fridge confirm screen. **Start lab** and **Not my dish**.
3. **Start lab.** Per dish action (see below).
4. **Explore.** Numbered steps stay visible. **I'm ready for the quiz** button.
5. **Quiz.** Two multiple choice questions. Wrong answer shows a hint and allows retry.
6. **Wrap up.** "Clean up before your receipt" with short cleanup instructions, then **Print my receipt**. Guests clean up first because they leave as soon as the receipt prints.
7. **Print.** Receipt prints. "Your receipt is on its way. Pick it up from the printer." **Next guest** returns to Scan. A print error shows the message, **Next guest** and **Staff: print again**.

## Fridge wall

The 2 fridge laptops run the same app with `.\start.ps1 fridge`; the cooking stations use `.\start.ps1 station`. No laptop needs its own setup. They are touch kiosks:

1. **Menu.** "Pick a dish by what you want to learn. Each takes about 5 minutes." The four dishes, each with its lab name and a one line `pitch`. The menu does not mention stations: the done screen and the ticket do.
2. **Confirm.** The chosen dish, then `uses` (the products and tools in the lab), then "You'll learn" with the `about` points. **Print my ticket** and **Back to menu**. Returns to the menu after 30 seconds.
3. **Ticket.** "Take your ticket". Returns to the menu after 12 seconds. A print error shows the message and a **Try again** button; the kiosk never retries on its own.

The ticket is a kitchen chit: the Mona chef wordmark from the receipt, an inverted "Kitchen ticket" bar, the date and time, "1x" and the dish in large type, a large QR code with the dish ID only, "Take this to any open station and scan it" and Microsoft Ignite 2026. It has no order number, since nothing reads one.

## Per dish start and wrap up

| Dish | Start lab | Wrap up |
|---|---|---|
| Omelette | Show instructions: open the Copilot app from the taskbar, start a **Canvas 101** session, paste "Open the Chez Mona Order Ticket canvas" | Delete the chat session (exact menu label to confirm) |
| Fried Chicken | Copy the pristine `copilot-sdk/` starter to a fresh temp folder. Explore step 1 has an **Open in VS Code** button that runs `code <folder>`. It focuses the window if it is open, or opens it again if the guest closed it | Launcher closes the VS Code window it opened and deletes the temp folder |
| Soup | Nothing to open yet: the concept steps come first, and step 3 has an **Open workflow file** button for the pinned file on GitHub.com | Close the browser tabs |
| Dip | Show instructions. Each step opens one comment or the review on GitHub.com when the guest clicks its button | Close the browser tabs |

## Lab content

The launcher reads all lab text, quiz choices and hints from [`launcher/content/labs.json`](launcher/content/labs.json). Each dish has a `pitch` for the menus, and `uses` and `about` points for the fridge confirm screen and the station intro. The quiz answers below are the source; the other choices and hints are drafted there.

### Omelette: GitHub Copilot app Canvas

- Learn: canvases are interactive panels that you and the agent both drive.
- Steps:
  1. In the taskbar, click the GitHub Copilot app icon to open it.
  2. On the left, find **Canvas 101**. Hover over it, then click **+** (New session) on the right. The step shows a screenshot of the button.
  3. Copy the prompt "Open the Chez Mona Order Ticket canvas" with the **Copy** button and paste it into the chat.
  4. Follow the instructions in the canvas: click to add a dish, then ask the agent to add or remove a dish. Return to the launcher and click **I'm ready for the quiz**.
- Quiz:
  1. Who can change a canvas? Answer: you and the agent.
  2. Where does a repository scoped canvas live? Answer: `.github/extensions/`.
- Receipt QR: https://docs.github.com/en/copilot/how-tos/github-copilot-app/working-with-canvas-extensions
- Design note: the canvas always opens with an empty ticket, so no reset is needed.

### Fried Chicken: Copilot SDK

- Learn: the SDK lets your app run a Copilot agent with your own tools.
- Starter: [`copilot-sdk/`](copilot-sdk/), a single `main.py` menu assistant. Its `get_menu` tool takes a `vegetarian_only` flag; the prompt asks for vegetarian dishes, so the agent chooses the argument itself. No `.git` folder, no push remote. Pinned to `github-copilot-sdk==1.0.28`, verified running on Windows with Python 3.12.
- Steps:
  1. Open VS Code with the **Open in VS Code** button.
  2. Open Copilot Chat (**Ctrl+Alt+I** if it is hidden).
  3. Ask: "What does define_tool do?"
  4. Ask: "How does the agent get the menu?"
  5. Optional: run the sample with `uv run main.py`.
- Quiz:
  1. How do you give the agent a custom tool? Answer: `define_tool`, then pass it in `tools=[...]`.
  2. Which call sends a prompt and waits for the reply? Answer: `send_and_wait`.
- Receipt QR: https://github.com/github/copilot-sdk/blob/main/python/README.md

### Soup: Agentic Workflows

- Learn: an agentic workflow is a GitHub Actions workflow written in Markdown. Frontmatter sets the trigger, permissions and allowed outputs; the body tells the agent what to do in plain language.
- Source: [`weekly-workshop-triage.md`](https://github.com/github-samples/tailspin-toys/blob/5cea2126c68a80d29f771ef14eb9e8cac0c91f65/.github/workflows/weekly-workshop-triage.md) in upstream `github-samples/tailspin-toys`, pinned to commit `5cea212` so later changes do not affect the lab. No booth copy and nothing to run; guests only read.
- Steps:
  1. Meet agentic workflows: one short definition.
  2. Read the frontmatter: explains the settings block and lists `on:`, `permissions:` and `safe-outputs:`. **Open frontmatter** opens the pinned file at lines 1 to 45 (`?plain=1#L1-L45`).
  3. Read the instructions: explains the plain-language prompt and lists **What to do**, **Never close these** and **When in doubt**. **Open instructions** opens lines 47 to 146 (`?plain=1#L47-L146`).
- The line ranges match commit `5cea212`. Update them if the pinned commit changes.
- The receipt QR links to [GitHub Agentic Workflows](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/about-github-agentic-workflows) on GitHub Docs for the full concepts.
- Quiz:
  1. When does it run? Answer: every Monday on a schedule, or manually on demand.
  2. What does the agent do when unsure? Answer: leaves the item open.
- Receipt QR: https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/about-github-agentic-workflows

### Dip: PR review

- Learn: two kinds of AI review meet on one pull request. Code scanning finds a known vulnerability and Copilot Autofix suggests a fix; Copilot code review reviews the whole change and comments like a teammate.
- Source: [`madebygps/chez-mona-dip`](https://github.com/madebygps/chez-mona-dip), a tiny public Chez Mona app (Express and SQLite) with one open PR, ["Add menu search"](https://github.com/madebygps/chez-mona-dip/pull/2). `main` is already rate limited so CodeQL comments only on the SQL injection. Public so CodeQL and Autofix need no Code Security license. Security pattern inspired by Lab 3 of `github-samples/securing-your-code`.
- Planted issues in the PR:
  - Security (for code scanning and Autofix):
    ```js
    const term = req.query.q;
    db.all(`SELECT * FROM dishes WHERE name LIKE '%${term}%'`, (err, rows) => {
    ```
    Autofix suggestion on the PR:
    ```js
    db.all('SELECT * FROM dishes WHERE name LIKE ?', [`%${term}%`], (err, rows) => {
    ```
  - Logic bug (for Copilot code review): `GET /dishes/search` is registered after `GET /dishes/:id`, so Express matches `search` as an ID and the new route always returns `404 Dish not found`. The new route also returns raw database error messages.
- Preparation: request one Copilot code review on the PR before the event, using [Max effort](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review#review-effort-level) to show the Universe 2026 launch. Guests only read the existing comments, so no review runs per guest.
- Why a PR: both the Autofix and code review comments stay on the PR and are visible to anyone who can see it.
- Freeze after preparation, so the PR never needs resetting:
  - A ruleset blocks pushes to the PR branch and merges into `main`.
  - No new review can start: automatic review only runs on open, first draft to open, or new pushes, and pushes are blocked.
  - Lock the PR conversation and leave every comment unresolved.
- Steps:
  1. Read the code scanning alert: **Open alert** opens the CodeQL comment (`files#discussion_r4461811755`). Look for its title and flagged line.
  2. Read the Autofix: find **Suggested changeset** under the same alert. No button.
  3. Read the Copilot review: **Open review** opens the review overview on the Conversation tab (`#pullrequestreview-5772715680`).
  4. Read the route comment: **Open comment** opens the Copilot comment about the shadowed search route (`files#discussion_r4470875041`).
- The comment and review IDs stay fixed because the PR is frozen. Update them if the PR is recreated.
- Quiz:
  1. What did code scanning find? Answer: SQL injection. Other choices: exposed secret, outdated dependency, cross site scripting. Hint: user input ends up inside a database query.
  2. Which reviewer looks at the whole change, not only known vulnerability patterns? Answer: Copilot code review. Other choices: code scanning, Copilot Autofix, the PR author. Hint: find the comment that is not about the SQL query.
- Receipt QR: https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review

## Receipt

The receipt is a keepsake guest check, designed to look different from the fridge ticket. From top to bottom:

- Gingham band, the Mona chef mark from the launcher UI beside the Chez Mona wordmark, Microsoft Ignite 2026, and the date and time. The receipt has no guest check number: stations don't share a counter, so a number could repeat.
- The dish as one line item ("1 lab")
- **You learned:** a one paragraph `receipt.summary` in [`labs.json`](launcher/content/labs.json), up to 180 characters, that sums up the `about` points. The quiz questions are not printed.
- Subtotal ("2/2 correct"), hints used (wrong quiz picks), tip ("Ship it!") and **Total: Priceless**
- QR code to the dish's docs link, captioned "Scan to continue learning at home"
- "Merci! Have a nice day", "Thanks for cooking with us" and a closing gingham band

The wordmark and gingham are raster images drawn with Windows fonts; if a font is missing, a plain built in font is used. The Mona chef mark is [`mona-chef.png`](launcher/chez_mona/mona-chef.png), a 512 px render of [`static/mona-chef.svg`](launcher/static/mona-chef.svg). Render it again if the SVG changes. The receipt has few blank lines, so it uses less paper.

### Printer integration

- Printer: [Rongta RP326](https://www.amazon.com/dp/B0CNT2F4Q5), 80 mm with auto cutter and USB, serial and Ethernet ports. Over USB it reports as "USB 80Series2" (USB ID `0FE6:811E`). It prints tickets and receipts correctly with the driverless USB connection on a Windows 11 ARM laptop.
- Each of the 8 laptops has its own USB receipt printer: 2 at the fridge wall and 6 at the cooking stations. No shared printer, network printer address or print server is required.
- No printer driver is needed. The localhost server writes raw ESC/POS bytes straight to the printer's USB printing interface, the same one the Windows spooler uses, without admin rights. The browser does not send printer commands directly.
- Before each job the launcher asks the printer for its state (ESC/POS `DLE EOT`) and refuses to print if the cover is open or the paper is out. A write that does not finish within 20 seconds is cancelled and reported.
- Direct USB is the only connection. There is no Windows print queue fallback: all 8 laptops are the same Surface model as the one tested, vendor POS drivers are often x64 only and may not install on ARM laptops, and Windows 11 no longer ships the "Generic / Text Only" driver.
- Use native ESC/POS text and cut commands. Render the documentation QR code as a monochrome raster image because native QR command support is not confirmed.
- 80 mm paper, with 72 mm printable width (576 dots at 203 dpi), fixed in code.
- Show print errors explicitly. A completed write means "sent to printer", not proof that paper was printed. Do not automatically retry an uncertain submission and risk duplicate receipts.

## Idle handling

| Screen | Timeout | Action |
|---|---|---|
| Intro, Quiz, Wrap up, Print | about 2 minutes | "Still cooking?" prompt, then return to Scan |
| Explore | about 10 minutes | "Still cooking?" prompt, then return to Scan |

On timeout the launcher closes the VS Code window and temp folder it created. Browser tabs and the Copilot app chat are left for staff.

## Technical notes

- Camera access works on `localhost` because browsers treat it as a secure context.
- Use a JavaScript QR library (for example ZXing or jsQR). The built in `BarcodeDetector` is not available in Chrome on Windows.
- Use large, matte QR codes on tickets to cope with booth lighting.
- The local server prepares the SDK starter and launches VS Code. A hosted site could not do this.
- Pre stage the SDK runtime on each laptop: `uv run --with github-copilot-sdk==1.0.28 python -m copilot download-runtime` from `launcher/`. It caches the runtime per user in `%LOCALAPPDATA%\github-copilot-sdk`, so no system Python is needed.
- Install and update the launcher on all laptops with a script, possibly extending `octobooth-demos/machine-setup`.

## Accidental change protection

- Booth account has no write access to the Soup and Dip repos.
- SDK starter is a fresh copy each time, with no `.git` and no push remote.
- Booth account has read only access to the booth repo and `canvas-101`, so changes made on a laptop cannot be pushed.
- `canvas-101`'s `AGENTS.md` tells the agent not to edit, commit or publish files during guest sessions.

## To verify before the event

- [x] Dip's PR shows the code scanning comment, its Autofix diff and Copilot code review comments to readers without write access (checked signed out, Nov 4). **Dismiss alert** is disabled; **Commit suggestion** is shown but cannot commit (no write access, ruleset blocks pushes)
- [x] CodeQL flags the Dip search line (`js/sql-injection` on line 51) and Autofix suggests a parameterized fix
- [x] Copilot code review flags the planted logic bug, and its comments are short enough to read within the time limit (Max effort, 4 comments of 200 to 300 characters)
- [x] Dip PR frozen: ruleset "Freeze booth lab" restricts updates, deletion and force pushes on `main` and `menu-search`; conversation locked
- [ ] Canvas opens with an empty ticket each time, and loads quickly
- [ ] Exact label for deleting a chat in the Copilot app
- [ ] Whether the launcher can open the Copilot app directly
- [ ] Shared booth account works for Copilot Chat in VS Code and for the SDK
- [ ] Shared account use is permitted, and quota is enough for booth traffic
- [ ] Webcam scanning speed under booth lighting (a printed ticket scanned with the Surface front camera in Edge app mode, Nov 4)
- [ ] Each lab fits in about 5 minutes on booth laptops
- [x] Printer model chosen: Rongta RP326, works with the driverless USB connection (Nov 4)
- [x] Receipt and ticket print with RAW ESC/POS on the RP326: raster QR scans with a phone, text fits, paper cuts (Nov 4)
- [x] `code --disable-workspace-trust` opened the guest folder on `main.py` with no Workspace Trust prompt (Nov 4)
- [x] Launcher closes only the VS Code window it opened (matched by the guest folder name in the window title), and **Open in VS Code** brings it back after a guest closes it (Nov 4)
- [ ] GitHub links from the launcher open in a normal browser window when the launcher runs in Edge app mode
- [ ] The other 7 RP326 units print the same way on their laptops
- [ ] Receipt QR codes scan reliably with a phone on the actual paper
- [ ] Redesigned ticket and receipt on the RP326: inverted bars (ESC/POS `GS B`) print white on black, raster wordmark and gingham look clean, and the receipt length is acceptable
- [ ] Missing printer, paper-out and cover-open handling on the real printer (the status query works; failures not yet triggered on hardware)
