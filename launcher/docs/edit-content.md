# Edit lab content

All lab content is in [`launcher/content/labs.json`](../content/labs.json).

Each dish has:

- **Menu and intro:** `pitch` for the menu, and `uses` and `about` points for the confirm and intro screens.
- **Steps:** a short `text` title, an optional lighter `body` line, an optional `image` under [`static/`](../static/) with `alt` text, and an optional `prompt` shown with a **Copy** button.
- **Quiz:** exactly two questions, each with an answer, three other choices and a hint.
- **Wrap up:** the clean up points.
- **Receipt:** `receipt.summary` (one short paragraph) and the QR link.

Rules:

- In text, use only `` `code` `` and `**bold**`.
- Receipts print in plain ASCII, so other characters show as `?`.
- The server checks the file at start. It refuses to run if something is missing, for example a quiz without exactly two questions and three other choices, a link that is not `https`, or a Markdown page that does not exist.

After you edit, [run the tests](test.md).
