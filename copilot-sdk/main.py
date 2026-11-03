"""Chez Mona menu assistant: a Copilot agent that calls your own Python code."""

import asyncio

from pydantic import BaseModel, Field

from copilot import CopilotClient, define_tool
from copilot.session import PermissionHandler

MENU = [
    {"dish": "Omelette", "price": 9, "vegetarian": True},
    {"dish": "Fried Chicken", "price": 14, "vegetarian": False},
    {"dish": "Soup", "price": 7, "vegetarian": True},
    {"dish": "Dip", "price": 6, "vegetarian": True},
]


class GetMenuParams(BaseModel):
    vegetarian_only: bool = Field(
        default=False, description="Only return vegetarian dishes"
    )


@define_tool(description="Get tonight's Chez Mona menu")
async def get_menu(params: GetMenuParams) -> list[dict]:
    print(f"[agent called get_menu(vegetarian_only={params.vegetarian_only})]")
    if params.vegetarian_only:
        return [item for item in MENU if item["vegetarian"]]
    return MENU


async def main():
    async with CopilotClient() as client:
        async with await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            tools=[get_menu],
        ) as session:
            reply = await session.send_and_wait(
                "I'm vegetarian. What can I order at Chez Mona tonight, and what's the cheapest?"
            )
            print(reply.data.content if reply else "No reply.")


asyncio.run(main())
