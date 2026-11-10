# Get lab counts

Each cooking station counts its own labs. The laptops do not share data, so get the counts from each station.

## See today's counts on the station

1. Press **Ctrl+Shift+M**, or hold the Chez Mona logo for 3 seconds.
2. Read the table at the bottom of the staff panel.

## Get a report to share

1. On the station, open PowerShell in the repo.
2. Run:

   ```powershell
   cd launcher
   uv run python -m chez_mona.stats
   ```

3. Copy the table. It is Markdown, so you can paste it into a GitHub issue. The first line shows the laptop name, so you can tell the stations apart.

For another day, add `--day 2026-11-18`. For every day in the log, add `--all`.

## What the counts mean

| Column | Counts when |
|---|---|
| Started | The guest taps **Start lab** and the lab starts. |
| Completed | The guest answers the last quiz question and Wrap up shows. Use this column for completions. |
| Receipts | The receipt prints. **Staff: print again** counts again. A failed print does not count. |

## Where the data is

The server adds one line to `launcher/data/events.jsonl` for each event. A line holds only the time, the event and the dish ID. Git ignores the `data/` folder. Do not delete it until you have the report.
