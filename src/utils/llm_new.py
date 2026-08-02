import traceback
import re
from openai import AsyncOpenAI

# Adjust these import paths to match your project structure
from src.models.queue import QueueItem
from api.db.database import Database
from api.models.models import BotConfig # We need a Pydantic model for config
from src.models.aicharacter import ActiveCharacter

def get_bot_config(db: Database) -> BotConfig:
    """Fetches all config key-values from the DB and returns a BotConfig object."""
    all_db_configs = db.list_configs()
    # Pydantic validates and provides default values for any missing keys
    return BotConfig(**all_db_configs)

async def generate_response(task: QueueItem, db: Database):
    """
    Generates an AI response for a given task using configuration from the database.
    Conditionally adds an assistant prefill message if enabled in the config.
    Supports both string-based prompts and structured messages_with_images.
    System prompt is placed below history for models that respond better to
    instructions arriving after visual context.
    """
    bot_config = get_bot_config(db)

    try:
        client = AsyncOpenAI(
            base_url=bot_config.ai_endpoint,
            api_key=bot_config.ai_key,
        )

        # --- MESSAGE BUILDING ---
        messages = []

        # History first, so the model sees the visual context early
        if task.messages_with_images:
            messages.extend(task.messages_with_images)

        # System prompt below the history — "later is louder"
        messages.append({
            "role": "system",
            "content": task.prompt
        })

        # The user's most recent message is cleaned and used in the user role
                # --- USER MESSAGE BUILDING WITH IMAGE SUPPORT ---
        user_clean = clean_string(task.message.content)

        # Build the user message as a content array if there are images
        user_attachments = [
            att for att in task.message.attachments
            if att.content_type and att.content_type.startswith("image/")
        ]

        if user_attachments:
            # Build the user message just like the history objects
            user_content_parts = []

            if user_clean:
                user_content_parts.append({"type": "text", "text": user_clean})

            for att in user_attachments:
                user_content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": att.url}
                })

            messages.append({
                "role": "user",
                "content": user_content_parts
            })
        else:
            # Old behavior: plain string
            messages.append({
                "role": "user",
                "content": user_clean
            })
        # --- END USER MESSAGE BUILDING ---


        # --- PREFILL LOGIC (unchanged) ---
        if bot_config.use_prefill:
            prefill_content = f"[Reply] {task.bot}:"
            messages.append({
                "role": "assistant",
                "content": prefill_content
            })
        # --- END PREFILL LOGIC ---

        completion = await client.chat.completions.create(
            model=bot_config.base_llm,
            stop=task.stop,
            max_tokens=8192,
            temperature=bot_config.temperature,
            messages=messages
        )

        result = completion.choices[0].message.content if completion.choices else "//[OOC: AI returned no response.]"
        result = result.replace("[Reply]", "").replace(f"{task.bot}:", "").strip()
        result = clean_thonk(result)
        task.result = result

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()

        print(f"Error in generate_response: {error_type}: {error_message}\n{error_traceback}")

        detailed_error = f"//[OOC: AI Error - {error_type}]\n"
        if hasattr(e, 'status_code'):
            detailed_error += f"Status Code: {e.status_code}\n"

        detailed_error += f"Task ID: {getattr(task, 'id', 'Unknown')}\n"
        detailed_error += f"Model: {bot_config.base_llm}\n"
        detailed_error += f"Message Length: {len(getattr(task.message, 'content', ''))}\n"
        detailed_error += f"Error Details: {error_message}"

        task.result = detailed_error

    return task



async def generate_blank(system: str, user: str, db: Database) -> str:
    """Generates a response from a simple system/user prompt pair."""
    bot_config = get_bot_config(db)
    try:
        client = AsyncOpenAI(
            base_url=bot_config.ai_endpoint,
            api_key=bot_config.ai_key,
        )
        completion = await client.chat.completions.create(
            model=bot_config.base_llm,
            temperature=bot_config.temperature,
            max_tokens=8192,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        result = completion.choices[0].message.content if completion.choices else "//[Error: No response]"
        return clean_thonk(result)
    except Exception as e:
        return f"//[OOC: Error in generate_blank: {e}]"


async def generate_in_character(character_name: str, system_addon: str, user: str, assistant: str, db: Database) -> str:
    """Generates a response 'in character' by dynamically loading the character from the DB."""
    bot_config = get_bot_config(db)
    try:
        # Fetch the character data from the database
        char_data = db.get_character(character_name)
        if not char_data:
            return f"//[OOC: Error: Character '{character_name}' not found in database.]"

        # Use the ActiveCharacter class to generate the character prompt part
        active_char = ActiveCharacter(char_data, db)
        character_prompt = active_char.get_character_prompt()

        # Combine the character prompt with any additional system instructions
        final_system_prompt = f"{character_prompt}\n{system_addon}"
        
        client = AsyncOpenAI(
            base_url=bot_config.ai_endpoint,
            api_key=bot_config.ai_key,
        )
        completion = await client.chat.completions.create(
            model=bot_config.base_llm,
            temperature=bot_config.temperature,
            max_tokens=8192,
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant}
            ]
        )
        result = completion.choices[0].message.content if completion.choices else "//[Error: No response]"
        return clean_thonk(result)
    except Exception as e:
        return f"//[OOC: Error in generate_in_character: {e}]"

# --- Utility Functions (Unchanged) ---

def clean_string(s: str) -> str:
    """Removes a 'Username: ' prefix if it exists."""
    return re.sub(r'^[^\s:]+:\s*', '', s) if re.match(r'^[^\s:]+:\s*', s) else s

def clean_thonk(s: str) -> str:
    """Recursively removes <think>...</think> blocks from the AI's output."""
    match = re.search(r'</think>', s, re.IGNORECASE)
    if match:
        # Find the start tag that corresponds to this end tag
        start_match = re.search(r'<think>', s[:match.start()], re.IGNORECASE)
        if start_match:
            # Remove the block and recurse on the rest of the string
            return clean_thonk(s[:start_match.start()] + s[match.end():])
    return s