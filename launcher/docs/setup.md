# Set up a booth laptop

Follow these steps once on each laptop. Steps marked **Person** need someone at the laptop. An agent can run the other steps.

## Cooking station

1. Check that winget works:

   ```powershell
   winget --version
   ```

   **Person:** If PowerShell cannot find `winget`, open the Microsoft Store, update **App Installer**, then try again.

2. Install Git, uv and VS Code. Edge comes with Windows.

   ```powershell
   winget install --exact --id Git.Git --accept-package-agreements --accept-source-agreements
   winget install --exact --id astral-sh.uv --accept-package-agreements --accept-source-agreements
   winget install --exact --id Microsoft.VisualStudioCode --accept-package-agreements --accept-source-agreements
   ```

3. **Person:** Install the GitHub Copilot app.
4. **Person:** Close every PowerShell window and the Copilot app, then open them again. Windows that were already open do not find the new tools.
5. Check the tools:

   ```powershell
   git --version
   uv --version
   code --version
   ```

6. **Person:** Sign in with the shared booth account in Edge (GitHub.com), VS Code (Copilot Chat) and the Copilot app.
7. Allow PowerShell scripts for this user:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
   ```

8. Clone this repo to the Desktop and install the launcher's packages:

   ```powershell
   cd ([Environment]::GetFolderPath('Desktop'))
   git clone https://github.com/madebygps/chez-mona-ignite-26.git
   cd chez-mona-ignite-26\launcher
   uv sync
   ```

9. Stage the Fried Chicken SDK runtime:

   ```powershell
   uv run --with github-copilot-sdk==1.0.28 python -m copilot download-runtime
   ```

   The output must show a line that starts with `Runtime cached at`.

10. Download the Fried Chicken sample's packages:

    ```powershell
    cd ..\copilot-sdk
    uv sync
    cd ..\launcher
    ```

11. **Person:** Open VS Code once and close the **Release Notes** tab. Then close VS Code.
12. **Person:** Pin the Copilot app to the taskbar.
13. **Person:** Connect the receipt printer by USB, load paper and turn it on. Connect no other USB printer.
14. Start the station:

    ```powershell
    .\start.ps1 station
    ```

15. **Person:** When Edge asks, allow camera access for `localhost`.
16. **Person:** Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
17. **Person:** Scan a fridge ticket. The station should open that dish's intro.
18. **Person:** Return to Scan, tap **Manually select a lab instead**, pick Fried Chicken and start the lab. Click **Open in VS Code**. VS Code should open `main.py`.
19. **Person:** In the Copilot app, click **+** next to **Sessions**. Click the model name in the chat box, turn on **Copilot Fusion** and check that **High** is available.
20. **Person:** Finish one Fried Chicken lab through the quiz. On the wrap up screen, check that its VS Code window closed.
21. **Person:** Click **Print my receipt**. A receipt should print and cut, and its QR code should scan with a phone.

## Fridge laptop

1. Check that winget works:

   ```powershell
   winget --version
   ```

   **Person:** If PowerShell cannot find `winget`, open the Microsoft Store, update **App Installer**, then try again.

2. Install Git and uv. Edge comes with Windows.

   ```powershell
   winget install --exact --id Git.Git --accept-package-agreements --accept-source-agreements
   winget install --exact --id astral-sh.uv --accept-package-agreements --accept-source-agreements
   ```

3. **Person:** Close every PowerShell window, then open PowerShell again. Windows that were already open do not find the new tools.
4. Check the tools:

   ```powershell
   git --version
   uv --version
   ```

5. Allow PowerShell scripts for this user:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
   ```

6. Clone this repo to the Desktop and install the launcher's packages:

   ```powershell
   cd ([Environment]::GetFolderPath('Desktop'))
   git clone https://github.com/madebygps/chez-mona-ignite-26.git
   cd chez-mona-ignite-26\launcher
   uv sync
   ```

7. **Person:** Connect the receipt printer by USB, load paper and turn it on. Connect no other USB printer.
8. Start the fridge:

   ```powershell
   .\start.ps1 fridge
   ```

9. **Person:** Press **Ctrl+Shift+M** and check that the staff panel shows the printer as ready. If it does not, check the cable, power, cover and paper, and close any other program that uses the printer.
10. **Person:** Tap a dish, then **Print my ticket**. A ticket should print and cut.
11. **Person:** Scan that ticket at a cooking station. The station should open the same dish.
