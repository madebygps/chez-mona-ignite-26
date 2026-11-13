# Booth staff brief

Read this before your shift. For full steps, see [Run the booth](run-booth.md).

## Clean idle stations

Each lab ends with a **Clean your station** step. Guests sometimes skip it. When you see an idle station, do the cleanup for that lab.

| Lab | Cleanup |
|---|---|
| Copilot Fusion Fusilli | In the Copilot app, delete the guest's chat. |
| Microsoft Copilot SDK Fried Chicken | Close the VS Code window. |
| Agentic Alphabet Soup | Close the browser tabs the guest opened. |
| Autofix Artichoke Dip | Close the browser tabs the guest opened. |

If a guest left mid-lab, also return the station to the Scan screen. Press **Ctrl+Shift+M** and use the staff panel.

## Fix printing problems

Most print errors come from the printer, not the app.

1. Check that the printer has paper and the cover is closed.
2. Check that the power cable and the USB cable are connected.
3. Press **Ctrl+Shift+M**. The staff panel shows if the printer is ready.
4. Print again:
   - Cooking station: on the Print screen, click **Staff: print again**.
   - Fridge: tap **Try again**. First check if the ticket printed, so the guest does not get two.

## Quick fixes

- **Guest has no ticket.** On the Scan screen, tap **Manually select a lab instead**.
- **Scanner does not read the ticket.** Check that Edge has camera access for `localhost`. Hold the ticket flat and still. If it still fails, pick the lab manually.
- **Staff panel.** Press **Ctrl+Shift+M**, or hold the Chez Mona logo for 3 seconds.
- **Station is stuck.** Press Ctrl+C in the launcher console, then run `.\start.ps1 station` again. Do not close the console first. See [Start a laptop](run-booth.md#start-a-laptop).
