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

The booth has 6 cooking station laptops and 2 fridge laptops, all on Windows. Each laptop has its own Rongta RP326 receipt printer, connected by USB.

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
6. Name the station, so its name and number prefix print on receipts. Create `launcher\station.json` with:

   ```json
   { "station_name": "Station 3", "number_prefix": "3" }
   ```

   Give each station its own prefix, `1` to `6`, so guest checks read `3-042` and no two stations print the same number. Every other setting already suits the booth. `station.json` is gitignored, so each laptop keeps its own.
7. Plug in the receipt printer by USB, load paper and turn it on. It needs no driver and no settings: the launcher uses the one USB printer it finds. Wi-Fi, network and virtual printers like "Microsoft Print to PDF" do not affect it.
8. Start the station:

   ```powershell
   .\start.ps1 station
   ```

9. When Edge asks, allow camera access for `localhost`. Edge remembers the choice.
10. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
11. Scan a fridge ticket. The station should open that dish's intro.
12. In the staff panel, pick Fried Chicken and start the lab. VS Code should open `main.py` with no Workspace Trust prompt. If the prompt appears, trust the parent folder `%LOCALAPPDATA%\ChezMona\guests` so later guests skip it. If VS Code does not open, add its `code.cmd` path to `station.json` as `code_path`.
13. In the Copilot app, select **canvas-101** and ask "Open the Chez Mona Order Ticket canvas". The canvas should open with an empty ticket.
14. Finish one dish through the quiz. A receipt should print and cut, and its QR code should scan with a phone.
15. Wrap up, then check that the Fried Chicken VS Code window closed.
16. Before the booth opens, delete `%LOCALAPPDATA%\ChezMona\guest-check.txt` so guest checks start at 001 again after the test receipts.

### Fridge laptop

Fridges only print tickets, so they skip VS Code, the SDK runtime, the Copilot app and the camera.

1. Install Git, Python 3.12, [uv](https://docs.astral.sh/uv/) and Microsoft Edge.
2. Clone this repo and install the launcher's packages:

   ```powershell
   git clone https://github.com/madebygps/chez-mona-ignite-26.git
   cd chez-mona-ignite-26\launcher
   uv sync
   ```

3. Give the fridge its number prefix, so its tickets read `A-042` and never match the other fridge's. Create `launcher\station.json` with:

   ```json
   { "number_prefix": "A" }
   ```

   Use `B` on the second fridge.
4. Plug in the receipt printer by USB, load paper and turn it on. It needs no driver and no settings.
5. Start the fridge:

   ```powershell
   .\start.ps1 fridge
   ```

6. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
7. Tap a dish, then **Print my ticket**. A ticket should print and cut, with its order number starting with the prefix.
8. Scan that ticket at a cooking station. The station should open the same dish.
9. Before the booth opens, delete `%LOCALAPPDATA%\ChezMona\fridge-order.txt` so order numbers start at 001 again after the test tickets.

If a printer only works through its vendor driver, install the driver, then set `printer_connection` to `queue` and `printer_queue` to the print queue name in `station.json`.

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
| `number_prefix` | empty | Up to 3 letters or digits put before this laptop's order or guest check numbers, for example `A` prints `A-042`. Use `A` and `B` on the fridges and `1` to `6` on the stations so no two laptops print the same number. Leave empty to print `042` |
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
