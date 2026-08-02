import copy
import discord
from jinja2 import Environment

# Adjust these import paths to match your project structure
from src.models.aicharacter import ActiveCharacter
from src.models.dimension import ActiveChannel
from src.plugins.manager import PluginManager
from src.controller.history import get_history, messages_to_string, get_history_with_image
from api.db.database import Database

# --- A sensible default template ---
# This template will be saved to the database if it doesn't exist.
DEFAULT_PROMPT_TEMPLATE = """\
<character_definition>
You are {{ character.name }}, you embody their character, persona, goals, personality, and bias which is described in detail below:
Your persona: {{ character.persona }}
A history reference to your speaking quirks and behavior:
{% for example in character.examples %}
[Reply] {{ example }} [End]
{% endfor %}
</character_definition>

<lore>
{{- channel.global_note if channel.global_note -}}
</lore>

<conversation_history>
{{ history }}
</conversation_history>

<instruction>
{{- character.instructions if character.instructions -}}
{{- channel.instruction if channel.instruction -}}

{# --- Dynamic Plugin Outputs --- #}
{% if plugins %}
{% for plugin_name, output_data in plugins.items() %}
    {# Loop through specific keys returned by the plugin (e.g. 'result', 'roll', 'reading') #}
    {% for key, value in output_data.items() %}
{{ value }}
    {% endfor %}
{% endfor %}
{% endif %}

[System Note: You are {{character.name}}. Answer only and only as {{character.name}}, don't reply as anyone else.]

</instruction>
"""
# Note: The '{{- ... -}}' syntax in Jinja2 removes leading whitespace for cleaner output.


class PromptEngineer:
    def __init__(self, bot: ActiveCharacter, message: discord.Message, channel: ActiveChannel,plugin_manager:PluginManager, messenger):
        self.bot = bot
        self.user_name = str(message.author.display_name)
        self.message = message
        self.channel = channel
        self.messenger = messenger
        
        # Get the database instance from one of the active models
        self.db: Database = bot.db
        
        self.plugin_manager = plugin_manager 
        self.jinja_env = Environment(trim_blocks=True, lstrip_blocks=True) # Recommended settings for prompt templates

        self.stopping_strings = ["[System", "(System", self.user_name + ":", "[End"] # Note make this not hardcoded

    def get_template_from_preset(self) -> str:
        """
        Retrieves the 'Default' preset template from the database.
        If the preset does not exist, it creates it with a default template
        and then returns it.
        """
        DEFAULT_PRESET_NAME = "Default"
        
        try:
            preset = self.db.get_preset(name=DEFAULT_PRESET_NAME)

            if not preset:
                # The preset does not exist, so we create it.
                print(f"Preset '{DEFAULT_PRESET_NAME}' not found. Creating it in the database...")
                self.db.create_preset(
                    name=DEFAULT_PRESET_NAME,
                    description="The default system prompt template, used as a fallback.",
                    prompt_template=DEFAULT_PROMPT_TEMPLATE
                )
                # Return the default template string we just saved
                return DEFAULT_PROMPT_TEMPLATE
            else:
                # The preset exists, return its template.
                # Provide a fallback to the default constant just in case the DB entry is empty.
                return preset.get('prompt_template') or DEFAULT_PROMPT_TEMPLATE

        except Exception as e:
            # If any database error occurs, log it and fall back to the default template
            print(f"Error accessing database for presets: {e}. Falling back to default template.")
            return DEFAULT_PROMPT_TEMPLATE

    async def create_prompt(self) -> dict:
        """
        Returns a dict with:
        - 'prompt': the old string prompt (unchanged behavior)
        - 'messages_with_images': the OpenRouter-style structured message list,
                                    with actual image URLs embedded. None if the
                                    history had no images.
        - 'history': the old string form of history (for templates)
        - 'history_messages_with_images': the structured form (for templates that want it)
        """
        formatted_history = await get_history_with_image(self.message.channel, self.db)
        history = messages_to_string(formatted_history)                # old string form
        history_messages_with_images = formatted_history                # new structured form

        inner_context = {
            "char": self.bot.name,
            "user": self.user_name
        }

        rendered_character = copy.deepcopy(self.bot)
        for field in ("persona", "instructions"):
            value = getattr(rendered_character, field)
            if value:
                setattr(rendered_character, field, self.jinja_env.from_string(value).render(inner_context))

        if rendered_character.examples:
            rendered_character.examples = [
                self.jinja_env.from_string(ex).render(inner_context)
                for ex in rendered_character.examples
            ]

        plugin_outputs = await self.plugin_manager.scan_and_execute(
            self.message, self.bot, self.channel, self.db, self.messenger
        )

        base_context = {
            "character": rendered_character,
            "channel": self.channel,
            "user": self.user_name,
            "history": history,
            "history_messages_with_images": history_messages_with_images,
            "message": self.message,
            "plugins": plugin_outputs,
        }

        template_str = self.get_template_from_preset()
        template = self.jinja_env.from_string(template_str)
        rendered_prompt = template.render(base_context)

        print(f"=====================\nFINAL PROMPT (string)\n=======================\n{rendered_prompt}")

        return {
            "prompt": rendered_prompt,                     # old string form
            "messages_with_images": history_messages_with_images,  # explicit new form
        }
