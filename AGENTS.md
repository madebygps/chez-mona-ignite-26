# Chez Mona, Microsoft Ignite 2026

This is the booth repository for the Chez Mona labs. [SPEC.md](SPEC.md) describes the launcher and every lab.

## Canvas 101 lab

Guests use the ticket; its author can also improve the canvas from this chat.

- When asked to open the canvas, open **Chez Mona Order Ticket** (`chez-mona-order-ticket`).
- For order requests, use canvas capabilities and actions to inspect or change the ticket. Do not edit source or stored ticket JSON to fulfill an order.
- When the user explicitly requests changes to the canvas interface, lesson, wording, layout or behavior, edit this worktree's existing extension source. Preserve the current ticket and unrelated changes; do not create a replacement canvas. Refresh the existing panel after changes. These authoring requests are allowed, not restricted to ticket actions.
- `add_dish` and `remove_dish` accept a menu dish ID and quantity. `get_ticket` returns the menu and current order. `clear_ticket` empties it.
- When asked what is on the ticket, call `get_ticket` and answer from its current state, including the guest's direct changes. Never infer the order from earlier chat messages.
- If an order is ambiguous, ask which dish. Report unavailable extension capabilities explicitly rather than pretending an action succeeded.
- Keep replies short. Explain how canvases work only when asked.
- Do not install packages for the extension SDK; the Copilot app supplies it.

## Repository

- Publishing changes is allowed when the user requests it. Do not publish session artifacts, guest ticket data or secrets.
