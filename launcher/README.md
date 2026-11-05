# Chez Mona launcher

Local web app that runs the booth flow on each laptop: scan a fridge ticket, read the intro, explore the lab, take a two question quiz, print a receipt and wrap up. The same app also runs the fridge wall kiosks that print the tickets. [SPEC.md](../SPEC.md) describes the flow and every lab.

A small Python server listens on `localhost` only. It serves the page and does the local work the browser cannot: copy the Fried Chicken starter, open and close VS Code, and send tickets and receipts to the printer.

## Layout

| Path | Contents |
|---|---|
| [`chez_mona/`](chez_mona/) | Server (`server.py`), Fried Chicken VS Code session (`sdk_session.py`), ticket and receipt layouts (`receipt.py`), fridge order and guest check numbers (`orders.py`), USB and Windows queue printing (`printer.py`), station settings (`config.py`), content loader (`labs.py`) |
| [`content/labs.json`](content/labs.json) | Every dish: intro line, steps, quiz with other choices and hints, wrap up, receipt takeaways (`receipt.learned`, 1 to 4 short points) and QR link |
| [`content/soup/`](content/soup/) | Soup concept pages, rendered in the launcher |
| [`static/`](static/) | The cooking station page (`index.html`, `app.js`), the fridge page (`fridge.html`, `fridge.js`), shared `app.css`, and vendored [jsQR](https://github.com/cozmo/jsQR) for webcam scanning |
| [`station.example.json`](station.example.json) | Every station setting at its default. Copy it to `station.json` only on a laptop that needs to change one |
| [`start.ps1`](start.ps1) | Starts a cooking station (`.\start.ps1 station`) or a fridge kiosk (`.\start.ps1 fridge`) and opens it in an Edge app window |
| [`tests/`](tests/) | Unit tests |

## Set up a laptop

The booth has 6 cooking station laptops and 2 fridge laptops. Each laptop has its own Rongta RP326 receipt printer, connected by USB. Every laptop runs Windows.

The defaults suit the booth, so most laptops need no settings file. If a laptop does need one (for example, VS Code is not found), copy `station.example.json` to `station.json` and change only that setting (see [Station settings](#station-settings)). `station.json` is gitignored.

The printer needs no driver and no settings. The launcher uses the one USB printer it finds. Wi-Fi printers, network printers and virtual printers like "Microsoft Print to PDF" do not affect it.

### Cooking station checklist

Install and sign in:

- [ ] Install Git, Python 3.12, [uv](https://docs.astral.sh/uv/), Microsoft Edge, VS Code and the GitHub Copilot app.
- [ ] Sign in with the shared booth account in Edge (GitHub.com), VS Code (Copilot Chat) and the Copilot app.
- [ ] Clone this repo, then install the launcher's packages:

  ```powershell
  git clone https://github.com/madebygps/chez-mona-ignite-26.git
  cd chez-mona-ignite-26\launcher
  uv sync
  ```

- [ ] Stage the Fried Chicken SDK runtime:

  ```powershell
  pip install -r ..\copilot-sdk\requirements.txt
  python -m copilot download-runtime
  ```

- [ ] Clone [madebygps/canvas-101](https://github.com/madebygps/canvas-101) and add it to the Copilot app for Omelette.
- [ ] Optional: to print the station name on receipts, create `station.json` with `{ "station_name": "Station 3" }`.

Connect and start:

- [ ] Plug in the receipt printer by USB, load paper and turn it on.
- [ ] Start the station:

  ```powershell
  .\start.ps1 station
  ```

- [ ] When Edge asks, allow camera access for `localhost`. Edge remembers the choice.

Check:

- [ ] Press **Ctrl+Shift+M**, and check the staff panel shows the printer as ready.
- [ ] Scan a fridge ticket. The station should open that dish's intro.
- [ ] In the staff panel, start Fried Chicken. VS Code should open `main.py` with no Workspace Trust prompt. If the prompt appears, trust the parent folder `%LOCALAPPDATA%\ChezMona\guests` so later guests skip it.
- [ ] In the Copilot app, select **canvas-101** and ask "Open the Chez Mona Order Ticket canvas". The canvas should open with an empty ticket.
- [ ] Finish one dish through the quiz. A receipt should print and cut, and its QR code should scan with a phone.
- [ ] Wrap up, then check that the Fried Chicken VS Code window closed.
- [ ] Before the booth opens, delete `%LOCALAPPDATA%\ChezMona\guest-check.txt` so guest checks start at 001.

### Fridge laptop checklist

Fridges only print tickets, so they need no VS Code, SDK runtime, Copilot app, camera or GitHub sign in beyond cloning this repo.

Install:

- [ ] Install Git, Python 3.12, [uv](https://docs.astral.sh/uv/) and Microsoft Edge.
- [ ] Clone this repo, then install the launcher's packages:

  ```powershell
  git clone https://github.com/madebygps/chez-mona-ignite-26.git
  cd chez-mona-ignite-26\launcher
  uv sync
  ```

Connect and start:

- [ ] Plug in the receipt printer by USB, load paper and turn it on.
- [ ] Start the fridge:

  ```powershell
  .\start.ps1 fridge
  ```

Check:

- [ ] Press **Ctrl+Shift+M**, and check the staff panel shows the printer as ready.
- [ ] Tap a dish, then **Print my ticket**. A ticket should print and cut.
- [ ] Scan that ticket at a cooking station. The station should open the same dish.
- [ ] Before the booth opens, delete `%LOCALAPPDATA%\ChezMona\fridge-order.txt` so order numbers start at 001.

### If the printer is not ready

- Check that the USB cable is connected and the printer is on, that the cover is closed and that the printer has paper.
- Close any other program that is using the printer.
- If a printer only works through its vendor driver, install the driver. Then set `printer_connection` to `queue` and `printer_queue` to the name of the print queue.

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

To run the server alone: `uv run python -u -m chez_mona [--role station|fridge] [--config path] [--port N]`.

## Station settings

| Setting | Default | Meaning |
|---|---|---|
| `port` | `8765` station, `8766` fridge | Local port for the page |
| `role` | `station` | `station` for a cooking station, `fridge` for a fridge wall kiosk that prints tickets. `start.ps1` sets this from its first argument |
| `station_name` | empty | Name printed on the receipt's guest check, for example `Station 3`. Leave empty to print none |
| `printer_connection` | `usb` | `usb` writes straight to the first attached USB printer, with no driver. `queue` sends RAW bytes to the Windows print queue `printer_queue` |
| `printer_usb_match` | empty | With `usb`, use only a printer whose device path contains this text, for example `vid_0fe6` |
| `printer_queue` | `Chez Mona Receipt` | Windows print queue used when `printer_connection` is `queue` |
| `paper_mm` | `80` | Paper width, for reference |
| `print_width_dots` | `576` | Printable width in dots, a multiple of 8. Use `384` for 58 mm paper |
| `code_path` | empty | Full path to VS Code's `code.cmd`. When empty, the launcher checks `PATH` and the default install folders |
| `idle_seconds` | `120`, `600`, `30` | Seconds before the "Still cooking?" prompt on most screens (`default`) and on Explore (`explore`), then the prompt countdown (`prompt`) |
| `state_dir` | `%LOCALAPPDATA%\ChezMona` | Where a fridge keeps its last order number (`fridge-order.txt`) and a station its last guest check number (`guest-check.txt`). Delete a file to restart at 001 |

Unknown settings stop the launcher with an error, so typos show up at start.

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

The tests cover content validation, station settings, ESC/POS output for tickets and receipts, order and guest check numbers, the Fried Chicken session with a fake VS Code, and the server endpoints with a fake printer.
