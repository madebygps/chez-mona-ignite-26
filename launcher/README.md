# Chez Mona launcher

Local web app that runs the booth flow on each laptop: scan a fridge ticket, read the intro, explore the lab, take a two question quiz, print a receipt and wrap up. The same app also runs the fridge wall kiosks that print the tickets. [SPEC.md](../SPEC.md) describes the flow and every lab.

A small Python server listens on `localhost` only. It serves the page and does the local work the browser cannot: copy the Fried Chicken starter, open and close VS Code, and send tickets and receipts to the printer.

## Layout

| Path | Contents |
|---|---|
| [`chez_mona/`](chez_mona/) | Server (`server.py`), Fried Chicken VS Code session (`sdk_session.py`), ticket and receipt layouts (`receipt.py`), USB printing (`printer.py`), station role (`config.py`), content loader (`labs.py`) |
| [`content/labs.json`](content/labs.json) | Every dish: intro line, steps, quiz with other choices and hints, wrap up, receipt takeaways (`receipt.learned`, 1 to 4 short points) and QR link |
| [`content/soup/`](content/soup/) | Soup concept pages, rendered in the launcher |
| [`static/`](static/) | The cooking station page (`index.html`, `app.js`), the fridge page (`fridge.html`, `fridge.js`), shared `app.css`, and vendored [jsQR](https://github.com/cozmo/jsQR) for webcam scanning |
| [`start.ps1`](start.ps1) | Starts a cooking station (`.\start.ps1 station`) or a fridge kiosk (`.\start.ps1 fridge`) and opens it in an Edge app window |
| [`tests/`](tests/) | Unit tests |

## Set up a laptop

The booth has 6 cooking station laptops and 2 fridge laptops, all identical Surface laptops on Windows. Each laptop has its own Rongta RP326 receipt printer, connected by USB. There is nothing to configure: every station starts the same way, and so does every fridge.

### Cooking station

1. Install Git, Python 3.12, [uv](https://docs.astral.sh/uv/), Microsoft Edge, VS Code and the GitHub Copilot app.
2. Sign in with the shared booth account in Edge (GitHub.com), VS Code (Copilot Chat) and the Copilot app.
3. Clone this repo and install the launcher's packages:

   ```powershell
   git clone https://github.com/madebygps/chez-mona-ignite-26.git
   cd chez-mona-ignite-26\launcher
   uv sync
   ```

4. Stage the Fried Chicken SDK runtime:

   ```powershell
   pip install -r ..\copilot-sdk\requirements.txt
   python -m copilot download-runtime
   ```

5. Clone [madebygps/canvas-101](https://github.com/madebygps/canvas-101) and add it to the Copilot app. Omelette uses it.
6. Plug in the receipt printer by USB, load paper and turn it on. It needs no driver and no settings: the launcher uses the one USB printer it finds. Wi-Fi, network and virtual printers like "Microsoft Print to PDF" do not affect it.
7. Start the station:

   ```powershell
   .\start.ps1 station
   ```

8. When Edge asks, allow camera access for `localhost`. Edge remembers the choice.
9. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
10. Scan a fridge ticket. The station should open that dish's intro.
11. In the staff panel, pick Fried Chicken and start the lab. VS Code should open `main.py` with no Workspace Trust prompt. If the prompt appears, trust the parent folder `%LOCALAPPDATA%\ChezMona\guests` so later guests skip it.
12. In the Copilot app, select **canvas-101** and ask "Open the Chez Mona Order Ticket canvas". The canvas should open with an empty ticket.
13. Finish one dish through the quiz. A receipt should print and cut, and its QR code should scan with a phone.
14. Wrap up, then check that the Fried Chicken VS Code window closed.

### Fridge laptop

Fridges only print tickets, so they skip VS Code, the SDK runtime, the Copilot app and the camera.

1. Install Git, Python 3.12, [uv](https://docs.astral.sh/uv/) and Microsoft Edge.
2. Clone this repo and install the launcher's packages:

   ```powershell
   git clone https://github.com/madebygps/chez-mona-ignite-26.git
   cd chez-mona-ignite-26\launcher
   uv sync
   ```

3. Plug in the receipt printer by USB, load paper and turn it on. It needs no driver and no settings.
4. Start the fridge:

   ```powershell
   .\start.ps1 fridge
   ```

5. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
6. Tap a dish, then **Print my ticket**. A ticket should print and cut.
7. Scan that ticket at a cooking station. The station should open the same dish.

## Run

Each laptop runs one of the two programs. On the 6 cooking stations:

```powershell
cd launcher
.\start.ps1 station
```

On the 2 fridge laptops:

```powershell
cd launcher
.\start.ps1 fridge
```

The script starts the server, waits for it, then opens the page in an Edge app window: `http://localhost:8765` for a station and `http://localhost:8766` for a fridge, so both can run on one laptop for testing. Press Ctrl+C in the console to stop. On stop, a cooking station closes any Fried Chicken VS Code window and deletes its folder. Add `-NoBrowser` to skip the Edge window, or `-Port N` to use another port. If the port is already taken, for example by a second station window, the script stops with an error.

To run the server alone: `uv run python -u -m chez_mona [--role station|fridge] [--port N]`.

Everything else is fixed for the booth hardware: the one attached USB printer, 80 mm paper (576 printable dots), VS Code from `PATH` or its default install folder.

## Staff controls

- Press **Ctrl+Shift+M**, or hold the Chez Mona logo for 3 seconds, to open the staff panel. It lets you pick a dish without scanning, shows the printer status and returns to Scan.
- After a print error, the Print screen offers **Staff: print again**. The launcher never retries on its own, so a guest never gets two receipts by accident.
- Tickets hold only the dish ID: `omelette`, `fried-chicken`, `soup` or `dip`. Case does not matter, and spaces or underscores count as hyphens.
- On a fridge, **Ctrl+Shift+M** shows the printer status. After a ticket print error, **Try again** prints once more; check the printer first, because the first attempt may have printed.

## How Fried Chicken works

1. **Start lab** copies [`copilot-sdk/`](../copilot-sdk/) to `%LOCALAPPDATA%\ChezMona\guests\chez-mona-fried-chicken-<id>`, without caches or virtual environments. It adds workspace settings that turn on auto save, so closing never stops on an unsaved changes prompt.
2. It runs `code --new-window --disable-workspace-trust <folder> <folder>\main.py`.
3. **Reopen in VS Code** on Explore focuses the window, or opens a new one if the guest closed it.
4. Wrap up, the idle timeout and stopping the server close VS Code windows whose title contains the folder name, then delete the folder. Leftover folders are also removed when the server starts and before each new guest.

## Edit lab content

Edit [`content/labs.json`](content/labs.json). In text, use only `` `code` `` and `**bold**`. The server checks the file at start and refuses to run if something is missing, for example a quiz without exactly two questions and three other choices, a link that is not `https`, or a Markdown page that does not exist. Receipts print in plain ASCII, so other characters show as `?`.

## Test

```powershell
cd launcher
uv run python -m unittest discover -s tests
```

The tests cover content validation, the station role, ESC/POS output for tickets and receipts, the Fried Chicken session with a fake VS Code, and the server endpoints with a fake printer.
