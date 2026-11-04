# Chez Mona launcher

Local web app that runs the booth flow on each laptop: scan a fridge ticket, read the intro, explore the lab, take a two question quiz, print a receipt and wrap up. The same app also runs the fridge wall kiosks that print the tickets. [SPEC.md](../SPEC.md) describes the flow and every lab.

A small Python server listens on `localhost` only. It serves the page and does the local work the browser cannot: copy the Fried Chicken starter, open and close VS Code, and send tickets and receipts to the printer.

## Layout

| Path | Contents |
|---|---|
| [`chez_mona/`](chez_mona/) | Server (`server.py`), Fried Chicken VS Code session (`sdk_session.py`), ticket and receipt layouts (`receipt.py`), fridge order numbers (`orders.py`), Windows printing (`printer.py`), station settings (`config.py`), content loader (`labs.py`) |
| [`content/labs.json`](content/labs.json) | Every dish: intro line, steps, quiz with other choices and hints, wrap up, receipt line and QR link |
| [`content/soup/`](content/soup/) | Soup concept pages, rendered in the launcher |
| [`static/`](static/) | The cooking station page (`index.html`, `app.js`), the fridge page (`fridge.html`, `fridge.js`), shared `app.css`, and vendored [jsQR](https://github.com/cozmo/jsQR) for webcam scanning |
| [`station.example.json`](station.example.json) | Default station settings, copied to `station.json` per laptop |
| [`start.ps1`](start.ps1) | Starts the server and opens the page in an Edge app window |
| [`tests/`](tests/) | Unit tests |

## Set up a laptop

Needs Windows, Python 3.12, [uv](https://docs.astral.sh/uv/), Microsoft Edge and VS Code.

1. Clone this repo, then install the launcher's packages:

   ```powershell
   cd launcher
   uv sync
   ```

2. Copy `station.example.json` to `station.json` and edit it for this laptop (see [Station settings](#station-settings)). `station.json` is gitignored. On the 2 fridge laptops set `"role": "fridge"` and `"fridge_number"` to `1` or `2`; they skip steps 3 to 5.
3. Pre stage the Fried Chicken SDK runtime, as SPEC describes:

   ```powershell
   pip install -r ..\copilot-sdk\requirements.txt
   python -m copilot download-runtime
   ```

4. Start the launcher once and allow camera access for `localhost` when Edge asks. Edge remembers the choice.
5. Start Fried Chicken from the staff panel and check that VS Code opens `main.py` with no Workspace Trust prompt. If the prompt appears, choose to trust the parent folder `%LOCALAPPDATA%\ChezMona\guests` so later guests skip it.
6. Install the receipt printer driver and name its queue to match `printer_queue`. Print one receipt with `dry_run` off and check that the QR code scans and the paper cuts.

## Run

```powershell
cd launcher
.\start.ps1
```

The script starts the server, waits for it, then opens `http://localhost:8765` in an Edge app window. Press Ctrl+C in the console to stop. On stop, the launcher closes any Fried Chicken VS Code window and deletes its folder.

To run the server alone: `uv run python -u -m chez_mona [--config path] [--port N]`.

## Station settings

| Setting | Default | Meaning |
|---|---|---|
| `port` | `8765` | Local port for the page |
| `role` | `station` | `station` for a cooking station, `fridge` for a fridge wall kiosk that prints tickets |
| `fridge_number` | `1` | Fridge number printed on tickets |
| `dry_run` | `true` | When true, nothing is printed. The page shows a preview, and the ESC/POS bytes and a PNG are saved in `out/` |
| `printer_queue` | `Chez Mona Receipt` | Windows print queue that receives RAW ESC/POS bytes |
| `paper_mm` | `80` | Paper width, for reference |
| `print_width_dots` | `576` | Printable width in dots, a multiple of 8. Use `384` for 58 mm paper |
| `code_path` | empty | Full path to VS Code's `code.cmd`. When empty, the launcher checks `PATH` and the default install folders |
| `idle_seconds` | `120`, `600`, `30` | Seconds before the "Still cooking?" prompt on most screens (`default`) and on Explore (`explore`), then the prompt countdown (`prompt`) |
| `state_dir` | `%LOCALAPPDATA%\ChezMona` | Where a fridge keeps its last order number (`fridge-<n>-order.txt`). Delete the file to restart at 001 |

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

The tests cover content validation, station settings, ESC/POS output for tickets and receipts, fridge order numbers, the Fried Chicken session with a fake VS Code, and the server endpoints in dry run.
