import asyncio
import random
import re
import discord
import os
import uuid
from typing import Optional, List, Dict, Any

# Adjust import paths to match your project structure
from api.db.database import Database
from api.models.models import BotConfig
from src.utils.image_eval import describe_image
from src.utils.web_eval import fetch_body
from src.utils.discord_utils import extract_valid_urls


def get_bot_config(db: Database) -> BotConfig:
    """Helper to fetch all config key-values from the DB and return a BotConfig object."""
    return BotConfig(**db.list_configs())


class _HistoryFormatter:
    """Internal class to fetch and format Discord message history for an AI model."""

    def __init__(self, db: Database):
        self.db = db
        self.bot_config = get_bot_config(db)

    async def format_history(self, context: discord.abc.Messageable, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve and format message history as OpenRouter-compatible message objects."""
        # Fetch messages in reverse chronological order (newest first)
        messages = [msg async for msg in context.history(limit=limit)]

        tasks = [self._format_message(msg) for msg in messages]
        formatted_messages = await asyncio.gather(*tasks)

        # Filter out None values (e.g., ignored comments)
        history = [fm for fm in formatted_messages if fm]
        history.reverse()  # Put back into chronological order (oldest first)

        # Apply reset logic — find the index after the last [RESET]
        reset_idx = -1
        for i, msg in enumerate(history):
            # Check if the text content contains [RESET]
            text_content = msg["content"][0].get("text", "")
            if "[RESET]" in text_content:
                reset_idx = i
        if reset_idx != -1:
            history = history[reset_idx + 1:]
            # Clean the [RESET] marker from the first message if present
            if history:
                history[0]["content"][0]["text"] = history[0]["content"][0]["text"].replace("[RESET]", "").strip()

        return history

    async def _format_message(self, message: discord.Message) -> Optional[Dict[str, Any]]:
        """Formats a single Discord message into an OpenRouter-compatible object."""
        name = self._sanitize_name(message.author.display_name)
        raw_content = self._clean_content(message.content)

        if raw_content.startswith("//"):
            return None  # Ignore comments

        prefix = "[Reply]"
        if raw_content.startswith("^"):
            raw_content = raw_content[1:]

        # Build the content array as list of parts
        content_parts: List[Dict[str, Any]] = []

        # Text part
        text = f"{prefix} {name}: {raw_content} [End]" if raw_content else f"{prefix} {name}: [End]"

        # Check reply indicator (if message starts with ^, it's a reply — could add reply context later)
        content_parts.append({"type": "text", "text": text})

        # Image handling: append actual image URL if multimodal is enabled
        if message.attachments:
            image_attachments = [att for att in message.attachments if att.content_type and att.content_type.startswith("image/")]
            for att in image_attachments:
                # Check DB for cached caption first
                message_id_str = str(message.id)
                caption = self.db.get_caption(message_id_str)

                if self.bot_config.multimodal_enable:
                    # OpenRouter-style: embed the actual image URL
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": att.url}
                    })
                    # Also include caption as text context if we have one cached
                    if caption and "<ERROR>" not in caption:
                        content_parts.append({"type": "text", "text": f"[Attached Image Description: {caption}]"})
                else:
                    # Fallback: only include caption text if it exists (old behavior)
                    if caption and "<ERROR>" not in caption:
                        content_parts.append({"type": "text", "text": f"[Attached Image Description: {caption}]"})

        # Link handling: append site content summary as text
        link_caption = await self._get_link_caption(message)
        if link_caption:
            content_parts.append({"type": "text", "text": link_caption})

        return {"role": "user", "content": content_parts}

    async def _get_link_caption(self, message: discord.Message) -> Optional[str]:
        """Gets a summary of links in a message. Checks database first."""
        message_id_str = str(message.id)
        # Check database first
        caption = self.db.get_caption(message_id_str)
        if caption:
            return caption

        links = extract_valid_urls(message.content)
        if not links:
            return None

        tasks = [fetch_body(link) for link in links]
        captions = await asyncio.gather(*tasks, return_exceptions=True)

        clean_captions = [c for c in captions if isinstance(c, str) and c.strip()]
        if not clean_captions:
            return None

        new_caption = "<site_content>\n" + "\n".join(clean_captions) + "\n</site_content>"

        if new_caption and "<ERROR>" not in new_caption:
            self.db.set_caption(message_id_str, new_caption)

        return new_caption

    @staticmethod
    def _sanitize_name(name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_-]', '', str(name))

    @staticmethod
    def _clean_content(content: str) -> str:
        return re.sub(r'<@!?\d+>', '', content).strip()


# --- Public API Function ---
async def get_history(context: discord.abc.Messageable, db: Database, limit: int = 100) -> str:
    """
    Fetches and formats message history as OpenRouter-compatible message objects.

    Args:
        context: The Discord channel or DM to fetch history from.
        db: An active database connection instance.
        limit: The number of messages to fetch.

    Returns:
        A list of message dicts suitable for OpenRouter's /chat/completions API.
    """

    formatter = _HistoryFormatter(db)
    message = await formatter.format_history(context, limit=limit)
    return messages_to_string(message)


# --- Backwards Compatibility Helper ---
def messages_to_string(messages: List[Dict[str, Any]]) -> str:
    """
    Converts OpenRouter-format messages back to the old pure-string format.
    Useful for text-only models or debugging.
    """
    lines = []
    for msg in messages:
        parts = msg["content"]
        text_parts = [p["text"] for p in parts if p["type"] == "text"]
        image_parts = [p for p in parts if p["type"] == "image_url"]

        combined = " ".join(text_parts)
        if image_parts:
            # Old format had image descriptions inline — here we just note the image exists
            combined += f" [{len(image_parts)} image(s) attached]"
        lines.append(combined)
    return "\n\n".join(lines)


# --- Public API Function ---
async def get_history_with_image(context: discord.abc.Messageable, db: Database, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches and formats message history as OpenRouter-compatible message objects.

    Args:
        context: The Discord channel or DM to fetch history from.
        db: An active database connection instance.
        limit: The number of messages to fetch.

    Returns:
        A list of message dicts suitable for OpenRouter's /chat/completions API.
    """

    formatter = _HistoryFormatter(db)
    return await formatter.format_history(context, limit=limit)