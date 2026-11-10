# Run the tests

Run the Python tests from `launcher`:

```powershell
cd launcher
uv run python -m unittest discover -s tests
```

These cover content validation, the station role, ESC/POS output for tickets and receipts, the Fried Chicken session with a fake VS Code, lab counts, and the server endpoints with a fake printer.

With Node.js installed, run the station UI tests from `launcher`:

```powershell
node --test tests\test_app.cjs
```

These cover manual lab selection, returning to scanning, and unavailable or pending cameras.
