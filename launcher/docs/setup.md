# Set up a booth laptop

Follow these steps once on each laptop. Every laptop gets the same setup, so it can run as a cooking station or a fridge. Steps marked **Person** need someone at the laptop. An agent can run the other steps.

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

Next, [start the laptop and check it](run-booth.md#check-a-new-laptop).
