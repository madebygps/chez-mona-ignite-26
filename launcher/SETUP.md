# Set up a booth laptop

The booth has 6 cooking station laptops and 2 fridge laptops, all identical Surface laptops on Windows. Each laptop has its own Rongta RP326 receipt printer, connected by USB. There is nothing to configure: every station starts the same way, and so does every fridge.

## Printer

The launcher talks to the printer directly over USB. It does not use a Windows print queue, a driver or a printer name.

- Connect the printer by USB only. The launcher ignores Wi-Fi, network and virtual printers like "Microsoft Print to PDF".
- Connect only one USB printer to each laptop. The launcher uses the first USB printer it finds.
- Use an ESC/POS printer with 80 mm paper. The launcher sends raw ESC/POS commands.
- Before each job, the launcher asks the printer for its status. It does not print if the cover is open or the paper is out.

## Cooking station

1. Install Git, [uv](https://docs.astral.sh/uv/), VS Code and the GitHub Copilot app. uv brings its own Python, and Edge comes with Windows.
2. Sign in with the shared booth account in Edge (GitHub.com), VS Code (Copilot Chat) and the Copilot app.
3. Allow PowerShell scripts for this user. Windows blocks them by default:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
   ```

4. Clone this repo and install the launcher's packages:

   ```powershell
   git clone https://github.com/madebygps/chez-mona-ignite-26.git
   cd chez-mona-ignite-26\launcher
   uv sync
   ```

5. Stage the Fried Chicken SDK runtime:

   ```powershell
   uv run --with github-copilot-sdk==1.0.28 python -m copilot download-runtime
   ```

6. Pin the Copilot app to the taskbar. Omelette uses it.
7. Plug in the receipt printer by USB, load paper and turn it on. It needs no driver and no settings: the launcher uses the one USB printer it finds. Wi-Fi, network and virtual printers like "Microsoft Print to PDF" do not affect it.
8. Start the station:

   ```powershell
   .\start.ps1 station
   ```

9. When Edge asks, allow camera access for `localhost`. Edge remembers the choice.
10. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
11. Scan a fridge ticket. The station should open that dish's intro.
12. Return to Scan, tap **Manually select a lab instead**, pick Fried Chicken and start the lab. Click **Open in VS Code**. VS Code should open `main.py` with no Workspace Trust prompt. If the prompt appears, trust the parent folder `%LOCALAPPDATA%\ChezMona\guests` so later guests skip it.
13. In the Copilot app, click **New chat**. Open the model picker and check that **Copilot Fusion** with **High** is available.
14. Finish one Fried Chicken lab through the quiz. On the wrap up screen, check that its VS Code window closed.
15. Click **Print my receipt**. A receipt should print and cut, and its QR code should scan with a phone.

## Fridge laptop

Fridges only print tickets, so they skip VS Code, the SDK runtime, the Copilot app and the camera.

1. Install Git and [uv](https://docs.astral.sh/uv/).
2. Allow PowerShell scripts for this user:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
   ```

3. Clone this repo and install the launcher's packages:

   ```powershell
   git clone https://github.com/madebygps/chez-mona-ignite-26.git
   cd chez-mona-ignite-26\launcher
   uv sync
   ```

4. Plug in the receipt printer by USB, load paper and turn it on. It needs no driver and no settings.
5. Start the fridge:

   ```powershell
   .\start.ps1 fridge
   ```

6. Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
7. Tap a dish, then **Print my ticket**. A ticket should print and cut.
8. Scan that ticket at a cooking station. The station should open the same dish.
