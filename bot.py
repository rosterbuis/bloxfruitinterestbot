import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = "https://bloxfruitinterest.onrender.com/api/interest"

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")


# --------------------------------------------------
# Tiny HTTP server for Render
# --------------------------------------------------

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(
                b"Blox Fruits Discord Bot is online!"
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_web_server():
    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"HTTP server listening on port {port}")
    server.serve_forever()


# --------------------------------------------------
# Discord bot
# --------------------------------------------------

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


async def get_fruit_interest(fruit):
    params = {
        "fruit": fruit
    }

    timeout = aiohttp.ClientTimeout(
        total=30
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        async with session.get(
            API_URL,
            params=params
        ) as response:

            text = await response.text()

            if response.status != 200:
                raise Exception(
                    f"API HTTP {response.status}: {text}"
                )

            return text.strip()


def parse_api_response(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    fruit_name = "Unknown"
    demand = "N/A"
    trend = "N/A"
    value = "N/A"
    interest_value = "N/A"

    if lines:
        fruit_name = lines[0]

        if fruit_name.startswith("🍇"):
            fruit_name = fruit_name[1:].strip()

    for line in lines:

        if line.startswith("Demand:"):
            demand = line.split(
                ":", 1
            )[1].strip()

        elif line.startswith("Trend:"):
            trend = line.split(
                ":", 1
            )[1].strip()

        elif line.startswith("Value:"):
            value = line.split(
                ":", 1
            )[1].strip()

        elif line.startswith("Interest:"):
            interest_value = line.split(
                ":", 1
            )[1].strip()

    return (
        fruit_name,
        demand,
        trend,
        value,
        interest_value
    )


@bot.event
async def on_ready():

    print("--------------------------------")
    print(f"Logged in as: {bot.user}")

    try:
        synced = await bot.tree.sync()

        print(
            f"Slash commands synced: {len(synced)}"
        )

    except Exception as error:
        print(
            f"Command sync error: {error}"
        )

    print(
        f"API: {API_URL}"
    )

    print("--------------------------------")


@bot.tree.command(
    name="interest",
    description="Check the interest of a Blox Fruits fruit."
)
@app_commands.describe(
    fruit="Fruit name, e.g. Kitsune"
)
async def interest(
    interaction: discord.Interaction,
    fruit: str
):

    await interaction.response.defer()

    fruit = fruit.strip()

    if not fruit:
        await interaction.followup.send(
            "❌ Please enter a fruit name."
        )
        return

    try:

        response = await get_fruit_interest(
            fruit
        )

        (
            fruit_name,
            demand,
            trend,
            value,
            interest_value
        ) = parse_api_response(
            response
        )

        embed = discord.Embed(
            title=f"🍇 {fruit_name}",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📊 Demand",
            value=demand,
            inline=True
        )

        embed.add_field(
            name="📈 Trend",
            value=trend,
            inline=True
        )

        embed.add_field(
            name="💰 Value",
            value=value,
            inline=True
        )

        embed.add_field(
            name="⭐ Interest",
            value=interest_value,
            inline=False
        )

        embed.set_footer(
            text="Blox Fruits Interest"
        )

        await interaction.followup.send(
            embed=embed
        )

    except Exception as error:

        await interaction.followup.send(
            "❌ Couldn't get that fruit.\n"
            f"`{str(error)[:500]}`"
        )


@bot.tree.command(
    name="api",
    description="Check if the Blox Fruits Interest API is online."
)
async def api(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                "https://bloxfruitinterest.onrender.com/"
            ) as response:

                if response.status == 200:

                    await interaction.followup.send(
                        "🟢 **API is online!**"
                    )

                else:

                    await interaction.followup.send(
                        f"🟠 API returned "
                        f"HTTP `{response.status}`."
                    )

    except Exception as error:

        await interaction.followup.send(
            "🔴 **API is unreachable.**\n"
            f"`{str(error)[:300]}`"
        )


# --------------------------------------------------
# Start HTTP server + Discord bot
# --------------------------------------------------

if __name__ == "__main__":

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    bot.run(TOKEN)