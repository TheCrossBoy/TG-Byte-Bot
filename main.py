import discord
import os
from dotenv import load_dotenv
import shelve

load_dotenv()

# Configuration settings
star_react = os.getenv('STAR_REACTION')
# allowed_categories = os.getenv('ALLOWED_CATEGORIES')
starboard_channel = os.getenv("STARBOARD_CHANNEL")
react_threshold = os.getenv("REACT_THRESHOLD")

# Administration settings
override_reaction = os.getenv("OVERRIDE_REACTION")
admin_id = int(os.getenv("ADMIN_ID"))

# Database import
db_file = os.getenv("DB_FILE")
persist = shelve.open(db_file, writeback=True)
if len(persist.keys()) == 0:
    persist['starred_messages'] = set()


# Button underneath starboard embed that has link to the original message
class ButtonLink(discord.ui.View):
    def __init__(self, msg_url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="Message", url=msg_url))


# Discord Bot
class ByteBot(discord.Client):
    # The channel where the starboard messages are sent
    starboard_channel = None

    async def on_ready(self):
        # Find our starboard channel
        self.starboard_channel = await self.fetch_channel(starboard_channel)
        print(f'Logged in as {self.user}!')

    async def on_raw_reaction_add(self, payload):
        # Only check messages not already added
        # if payload.message_id in persist['starred_messages']:
        #     return

        # Add message to the persist list so we don't use it again
        persist['starred_messages'].add(payload.message_id)

        # Fetch the structures for the message
        ch = await self.fetch_channel(payload.channel_id)
        msg = await ch.fetch_message(payload.message_id)
        user = await self.fetch_user(payload.user_id)
        if ch is None or msg is None or user is None:
            print(f'Error getting react information!\n{payload}')

        # Check the reaction info + counts
        for reaction in msg.reactions:
            if (reaction.emoji == star_react and reaction.count >= int(react_threshold)) \
                    or (payload.emoji.name == override_reaction and user.id == admin_id):
                print(f'Passed reaction threshold <{msg.id}>')
                await self.add_to_starboard(msg)
                return

    async def add_to_starboard(self, message):
        # Generate starboard embed
        embed = discord.Embed(
            description=message.content if len(message.content) <= 1000 else message.content[:1000] + "...",
            color=0xc29c0f)
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
        embed.set_footer(text=f'#{message.channel.name} - Message shortened to 1000 characters.')
        # If we have one image, attach in the embed
        print(message)
        print(message.content)
        print(message.embeds)
        print(message.attachments)
        if len(message.attachments) == 1 and message.attachments[0].content_type[:5] == "image":
            embed.set_image(url=message.attachments[0].url)

        # If we have multiples, put links so they're embedded still
        elif len(message.attachments) >= 1:
            content = "\n".join([a.url for a in message.attachments])
            if embed.description != "":
                embed.description += "\n" + content
            else:
                embed.description = content

        # Send the message, embed, and attach the button
        await self.starboard_channel.send(embed=embed, view=ButtonLink(message.jump_url))


try:
    # Generate intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True
    intents.members = True

    # Start our bot
    client = ByteBot(intents=intents)
    client.run(os.getenv('DISCORD_TOKEN'))
finally:
    # Save persistent data
    persist.close()
    print(f'Closed cleanly!')
