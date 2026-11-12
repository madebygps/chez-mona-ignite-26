# Start a laptop

Each laptop runs one of the two programs. Open PowerShell in the repo.

On the 6 cooking stations:

```powershell
cd launcher
.\start.ps1 station
```

On the 2 fridge laptops:

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

Everything else is fixed for the booth hardware: the one attached USB printer, 80 mm paper (576 printable dots), and VS Code from `PATH` or its default install folder.
