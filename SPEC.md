# Chez Mona lab launcher spec

Booth: Chez Mona, Microsoft Ignite 2026
Status: draft, planning only, nothing built yet

## Goal

A local web app on each booth laptop that turns a fridge ticket into a 5 minute lab:
scan ticket, read instructions, explore, answer a short quiz, print a receipt with a docs QR code.

## Decisions

| Area | Decision |
|---|---|
| Format | Explore, then quiz, then printed receipt |
| Machines and accounts | Booth provided, shared booth account |
| Launcher hosting | Local web app on each laptop, served on `localhost` |
| Laptop to lab mapping | Any laptop runs any dish, chosen by the scanned ticket |
| Ticket scanning | Laptop webcam, in the browser |
| Ticket QR content | Dish ID only, tickets are reusable |
| Wrong quiz answer | Show a hint, retry until correct |
| Abandoned lab | Idle prompt "Still cooking?", then return to scan screen |

## Lineup

| Dish | Lab | Explore surface | Prepared material |
|---|---|---|---|
| Omelette | Canvas 101 | GitHub Copilot app | Booth repo with the repository scoped Chez Mona order ticket canvas |
| Fried Chicken | Copilot SDK | VS Code with Copilot Chat | Small Python starter in the booth repo, based on the official SDK sample |
| Soup | Agentic Workflows | GitHub.com | Upstream [github-samples/tailspin-toys](https://github.com/github-samples/tailspin-toys) triage workflow file, pinned to a commit |
| Dip | Security | GitHub.com | Tiny booth owned Chez Mona repo with a SQL injection PR that already has a Copilot Autofix comment |

## Booth repository

One private repo, [madebygps/chez-mona-ignite-26](https://github.com/madebygps/chez-mona-ignite-26), cloned once on each laptop. It holds everything that runs locally:

| Path | Contents |
|---|---|
| `.github/extensions/chez-mona-order-ticket/` | Omelette canvas, moved from [madebygps/canvas-101](https://github.com/madebygps/canvas-101) |
| `copilot-sdk/` | Fried Chicken SDK starter |
| `launcher/` | Local launcher web app (to build) |

Soup and Dip are visited on GitHub.com, so they are not cloned. Soup uses the upstream `tailspin-toys` repo; Dip needs a separate booth owned repo.

## Screen flow

1. **Scan.** Webcam view with "Scan your ticket". Hidden staff fallback to pick a dish manually.
2. **Intro.** Dish name, one line on what you'll learn, **Start lab** button.
3. **Start lab.** Per dish action (see below).
4. **Explore.** Numbered steps stay visible. **I'm ready for the quiz** button.
5. **Quiz.** Two multiple choice questions. Wrong answer shows a hint and allows retry.
6. **Print.** Receipt prints. Screen confirms.
7. **Wrap up.** Short cleanup instructions, **Next guest** returns to Scan.

## Per dish start and wrap up

| Dish | Start lab | Wrap up |
|---|---|---|
| Omelette | Show instructions: open the Copilot app, select **chez-mona-ignite-26**, open a chat, ask "Open the Chez Mona Order Ticket canvas" | Delete the chat session (exact menu label to confirm) |
| Fried Chicken | Copy the pristine `copilot-sdk/` starter to a fresh temp folder, then open it with `code <folder>` | Launcher closes the VS Code window it opened and deletes the temp folder |
| Soup | Open the pinned workflow file on GitHub.com (see Soup lab content) | Close the browser tabs |
| Dip | Open the "Add menu search" PR on GitHub.com | Close the browser tabs |

## Lab content

### Omelette: Canvas 101

- Learn: canvases are interactive panels that you and the agent both drive.
- Steps:
  1. Open the canvas.
  2. Click to add a dish.
  3. Ask the agent to add or remove a dish, and watch the ticket update.
- Quiz:
  1. Who can change a canvas? Answer: you and the agent.
  2. Where does a repository scoped canvas live? Answer: `.github/extensions/`.
- Receipt QR: https://docs.github.com/en/copilot/how-tos/github-copilot-app/working-with-canvas-extensions
- Design note: the canvas always opens with an empty ticket, so no reset is needed.

### Fried Chicken: Copilot SDK

- Learn: the SDK lets your app run a Copilot agent with your own tools.
- Starter: [`copilot-sdk/`](copilot-sdk/), a single `main.py` menu assistant. Its `get_menu` tool takes a `vegetarian_only` flag; the prompt asks for vegetarian dishes, so the agent chooses the argument itself. No `.git` folder, no push remote. Pinned to `github-copilot-sdk==1.0.28`, verified running on Windows with Python 3.12.
- Steps:
  1. Open the starter in VS Code.
  2. Ask Copilot Chat: "What does `define_tool` do?" and "How does the agent get the menu?"
  3. Optional: run the sample.
- Quiz:
  1. How do you give the agent a custom tool? Answer: `define_tool`, then pass it in `tools=[...]`.
  2. Which call sends a prompt and waits for the reply? Answer: `send_and_wait`.
- Receipt QR: https://github.com/github/copilot-sdk/blob/main/python/README.md

### Soup: Agentic Workflows

- Learn: an agentic workflow is a GitHub Actions workflow written in Markdown. Frontmatter sets the trigger, permissions and allowed outputs; the body tells the agent what to do in plain language.
- Source: [`weekly-workshop-triage.md`](https://github.com/github-samples/tailspin-toys/blob/5cea2126c68a80d29f771ef14eb9e8cac0c91f65/.github/workflows/weekly-workshop-triage.md) in upstream `github-samples/tailspin-toys`, pinned to commit `5cea212` so later changes do not affect the lab. No booth copy and nothing to run; guests only read.
- Steps:
  1. Read the launcher's short explanation of agentic workflows.
  2. Open the pinned workflow file and read it: the frontmatter (trigger, permissions, safe outputs), then the instructions.
  3. Come back to the launcher for the quiz.
- Quiz:
  1. When does it run? Answer: every Monday on a schedule, or manually on demand.
  2. What does the agent do when unsure? Answer: leaves the item open.
- Receipt QR: Agentic Workflows docs (link to confirm).

### Dip: Security

- Learn: code scanning finds a vulnerability, Copilot Autofix suggests a fix.
- Source: a tiny booth owned Chez Mona app (Express and SQLite) with one open PR, "Add menu search". Pattern inspired by Lab 3 of `github-samples/securing-your-code`.
- Vulnerable line in the PR:
  ```js
  db.all(`SELECT * FROM dishes WHERE name LIKE '%${req.query.q}%'`)
  ```
- Autofix suggestion (expected shape, confirm against the real output):
  ```js
  db.all("SELECT * FROM dishes WHERE name LIKE ?", [`%${req.query.q}%`])
  ```
- Why a PR: the Autofix comment stays on the PR and is visible to anyone who can see the PR, unlike generating a fix on the alert page.
- Steps:
  1. Open the PR.
  2. Read the code scanning comment.
  3. Compare the original line with the Autofix suggestion.
- Quiz:
  1. What did code scanning find? Answer: SQL injection. Other choices: exposed secret, outdated dependency, cross site scripting. Hint: user input ends up inside a database query.
  2. How does the Autofix suggestion fix it? Answer: passes the search text as a parameter instead of pasting it into the SQL. Other choices: removes the search feature, escapes HTML, requires a login. Hint: compare the query lines and look for the `?`.
- Receipt QR: Copilot Autofix docs (link to confirm).

## Receipt

- Header: Chez Mona
- Dish name and lab name
- One line on what you learned
- QR code to the dish's docs link
- Footer: Microsoft Ignite 2026

### Printer integration

Current working plan from the printers and networks discussion; the printer model is not final.

- Each of the 8 laptops has its own USB receipt printer: 2 at the fridge wall and 6 at the cooking stations. No shared printer, network printer address or print server is required.
- Assuming Windows laptops, install the selected printer's driver and use the same print queue name on every laptop.
- The localhost server submits raw ESC/POS bytes to that laptop's configured Windows print queue, using the Windows spooler RAW datatype. The browser does not send printer commands directly.
- Use native ESC/POS text and cut commands. Render the documentation QR code as a monochrome raster image because native QR command support is not confirmed.
- Target 80 mm paper, with approximately 72 mm printable width (576 dots at 203 dpi), subject to verification on the selected model.
- Current model candidates are Rongta RP820 and RP326. Driver compatibility, raster printing and cutting must be verified on the actual hardware.
- Keep the queue name, paper width and printable dot width in station configuration so a model change or 58 mm fallback does not require code changes.
- Show print submission errors explicitly. Spooler acceptance means "sent to printer", not proof that paper was printed. Do not automatically retry an uncertain submission and risk duplicate receipts.

## Idle handling

| Screen | Timeout | Action |
|---|---|---|
| Intro, Quiz, Print, Wrap up | about 2 minutes | "Still cooking?" prompt, then return to Scan |
| Explore | about 10 minutes | "Still cooking?" prompt, then return to Scan |

On timeout the launcher closes the VS Code window and temp folder it created. Browser tabs and the Copilot app chat are left for staff.

## Technical notes

- Camera access works on `localhost` because browsers treat it as a secure context.
- Use a JavaScript QR library (for example ZXing or jsQR). The built in `BarcodeDetector` is not available in Chrome on Windows.
- Use large, matte QR codes on tickets to cope with booth lighting.
- The local server prepares the SDK starter and launches VS Code. A hosted site could not do this.
- Pre stage the SDK runtime on each laptop: `pip install -r copilot-sdk/requirements.txt`, then `python -m copilot download-runtime`. Requires Python 3.11 or later.
- Install and update the launcher on all laptops with a script, possibly extending `octobooth-demos/machine-setup`.

## Accidental change protection

- Booth account has no write access to the Soup and Dip repos.
- SDK starter is a fresh copy each time, with no `.git` and no push remote.
- Booth account has read only access to the booth repo, so changes made on a laptop cannot be pushed.

## To verify before the event

- [ ] Booth account can see the code scanning and Autofix comments on Dip's PR with read only access
- [ ] CodeQL flags the Dip search line and Autofix produces a clear parameterized fix
- [ ] Canvas opens with an empty ticket each time, and loads quickly
- [ ] Exact label for deleting a chat in the Copilot app
- [ ] Whether the launcher can open the Copilot app directly
- [ ] Shared booth account works for Copilot Chat in VS Code and for the SDK
- [ ] Shared account use is permitted, and quota is enough for booth traffic
- [ ] Webcam scanning speed under booth lighting
- [ ] Each lab fits in about 5 minutes on booth laptops
- [ ] Docs links for Agentic Workflows and Copilot Autofix
- [ ] Final printer model, Windows driver and configured queue name
- [ ] ESC/POS RAW printing, raster QR output and auto-cut on the selected printer
- [ ] Receipt QR codes scan reliably with a phone on the actual paper
- [ ] Missing printer, paper-out and uncertain print submission handling
