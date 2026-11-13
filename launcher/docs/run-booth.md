# Run the booth

## Start a laptop

Each laptop runs one of the two programs. Open PowerShell in the repo.

On a cooking station:

```powershell
cd launcher
.\start.ps1 station
```

On a fridge laptop:

```powershell
cd launcher
.\start.ps1 fridge
```

The script starts the server, waits for it, then opens the page in an Edge app window. A station uses `http://localhost:8765` and a fridge uses `http://localhost:8766`, so both can run on one laptop for testing.

- To stop, press Ctrl+C in the console. A cooking station then closes any Fried Chicken VS Code window and deletes its folder.
- Press Ctrl+C before you close the console. If you close it first, the server keeps running and its port stays busy. To stop every launcher server on the laptop, run:

  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='uv.exe' or Name='python.exe'" | Where-Object CommandLine -like '*-m chez_mona --port*' | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
  ```
- To skip the Edge window, add `-NoBrowser`.
- To use another port, add `-Port N`. If the port is already taken, for example by a second station window, the script stops with an error.
- To run the server alone: `uv run python -u -m chez_mona [--role station|fridge] [--port N]`.

### Launcher icon

Both pages use the Mona favicon. The icon files are in `launcher\static`:
`favicon.svg`, `favicon.ico` and `launcher-icon.png`.

These steps apply only to a normal Windows shortcut, not an Edge app window.
To use the icon on an existing Windows shortcut, open **Properties**.
Select **Change Icon**, then browse to `launcher\static\favicon.ico` in this repo.
Select the Mona icon and click **OK**, then **Apply**.
The launcher opens in an Edge app window. Edge controls that window's taskbar icon.
Changing a Windows shortcut icon does not change the Edge window's taskbar icon.
The ICO includes native sizes for common Windows display scales.
After an icon update, unpin the launcher shortcut from the taskbar.
Apply the updated icon to the shortcut, then pin it again.

## Check a new laptop

Do these checks after you [set up a laptop](setup.md) and start it for the first time.

### Cooking station

1. When Edge asks, allow camera access for `localhost`.
2. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
3. Scan a fridge ticket. The station should open that dish's intro.
4. Return to Scan, tap **Manually select a lab instead**, pick Fried Chicken and start the lab. Click **Open in VS Code**. VS Code should open `main.py`.
5. In the Copilot app, click **+** next to **Sessions**. Click the model name in the chat box, turn on **Copilot Fusion** and check that **High** is available.
6. Finish one Fried Chicken lab through the quiz. On the **Clean your station** screen, close the VS Code window and tick **Close the VS Code window.**
7. Click **Check, please!**. The screen should show the receipt with a rank stamp, and the printer should print and cut the same receipt. Its QR code should scan with a phone. Click **Next guest** and check that the lab folder is gone.

### Fridge

1. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
2. Tap a dish, then **Print my ticket**. A ticket should print and cut.
3. Scan that ticket at a cooking station. The station should open the same dish.

## Staff controls

### Cooking station

- **Pick a lab without a ticket.** Guests can tap **Manually select a lab instead** on the Scan screen. **Scan a ticket instead** returns to scanning.
- **Open the staff panel.** Press **Ctrl+Shift+M**, or hold the Chez Mona logo for 3 seconds. The panel lets you pick a dish without scanning, shows the printer status and today's [lab counts](#get-lab-counts), and returns to Scan.
- **Print a receipt again.** After a print error, the Print screen shows **Staff: print again**. The launcher never retries on its own, so a guest never gets two receipts by accident.

Receipts show a number beside the date and time, such as **Receipt #024**.
Each station numbers its own receipts across all dishes and days, using its event log.
Numbers continue after a restart. Each successful reprint gets a new number.

### Fridge

- **Check the printer.** Press **Ctrl+Shift+M**.
- **Print a ticket again.** After a ticket print error, tap **Try again**. Check the printer first, because the first attempt may have printed.

## Get lab counts

Each cooking station counts its own labs. The laptops do not share data, so get the counts from each station.

### See today's counts on the station

1. Press **Ctrl+Shift+M**, or hold the Chez Mona logo for 3 seconds.
2. Read the table at the bottom of the staff panel.

### Get a report to share

1. On the station, open PowerShell in the repo.
2. Run:

   ```powershell
   cd launcher
   uv run python -m chez_mona.stats
   ```

3. Copy the table. It is Markdown, so you can paste it into a GitHub issue. The first line shows the laptop name, so you can tell the stations apart.

For another day, add `--day 2026-11-18`. For every day in the log, add `--all`.

### What the counts mean

| Column | Counts when |
|---|---|
| Started | The guest taps **Start lab** and the lab starts. |
| Completed | The guest answers the last quiz question and Wrap up shows. Use this column for completions. |
| Receipts | The receipt prints. **Staff: print again** counts again. A failed print does not count. |

### Where the data is

The server adds one line to `launcher/data/events.jsonl` for each event. A line holds only the time, the event and the dish ID. Git ignores the `data/` folder. Do not delete it until you have the report.
