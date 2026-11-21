import discord
import asyncio
import os
import re
import urllib.request
import json

# ── CONFIG ──
TOKEN = "ODk0NDQ4MTg4MTkzMzk4ODI2.GM1Iq9.8qo5nxDnmBtaGuG5AHkDZQhd_8mEVeeID7G9bA"
CHANNEL_IDS = [1556149863190630411, 1556292827951145121, 1560229992611192852]
BOT_ID = 1558128230588878910

IGNORE_WORDS = {
    "scramble", "unscramble", "answer", "ended", "result", "no", "one", 
    "solved", "this", "round", "time", "seconds", "remaining", "eys", "hub",
    "the", "word", "is", "you", "have", "to", "guess", "type", "correct", 
    "good", "luck", "reward", "ends", "in", "minutes"
}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Tracks active scrambles: { channel_id: "scrambled_letters" }
ACTIVE_SCRAMBLES = {}

def solve_scramble(scramble):
    print(f"[*] Querying API for anagrams of: {scramble}")
    url = f"https://api.datamuse.com/words?rel_ana={scramble}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            valid_words = []
            for item in data:
                word = item['word'].upper()
                # Ensure exact letter count
                if len(word) == len(scramble):
                    valid_words.append(word)
            return valid_words
    except Exception as e:
        print(f"[-] API error: {e}")
        return []

def extract_scramble(text):
    # 1. Look for ALL CAPS words of 4+ letters (like IHENFRIDSP)
    # This bypasses the normal sentence text completely.
    caps_matches = re.findall(r'\b[A-Z]{4,}\b', text)
    if caps_matches:
        # Pick the longest all-caps word found
        return max(caps_matches, key=len).lower()

    # 2. Fallback: Check for spaced letters (e.g. "C O R A L")
    spaced_matches = re.findall(r'\b(?:[A-Za-z]\s+){3,}[A-Za-z]\b', text)
    if spaced_matches:
        best = max(spaced_matches, key=len)
        return best.replace(" ", "").lower()
        
    # 3. Fallback: Check for normal words, filtering out prompt words
    words = re.findall(r'[A-Za-z]+', text)
    valid = []
    for w in words:
        if w.lower() not in IGNORE_WORDS and len(w) >= 4:
            valid.append(w)
            
    if not valid:
        return None
    return max(valid, key=len).lower()

async def attempt_solve(channel, scramble):
    """Background task to try solutions every 5 seconds."""
    solutions = solve_scramble(scramble)
    if not solutions:
        print(f"[-] No solutions found for {scramble}")
        return

    # Datamuse returns sorted by frequency (most common first).
    # We'll keep the top 5 just in case.
    top_guesses = solutions[:5]

    for guess in top_guesses:
        # Check if the round is still active for this channel
        if ACTIVE_SCRAMBLES.get(channel.id) != scramble:
            print(f"[*] Round ended or changed for {channel.name}. Stopping.")
            return
            
        print(f"[*] Trying guess: {guess}")
        try:
            await channel.send(guess)
        except Exception as e:
            print(f"[-] Failed to send: {e}")
            
        # Wait 5 seconds before trying the next word
        await asyncio.sleep(5)

@client.event
async def on_ready():
    print(f"[+] Logged in as {client.user}")
    print(f"[*] Listening in {len(CHANNEL_IDS)} channels...")

@client.event
async def on_message(message):
    print(f"DEBUG: Saw message from {message.author.name} in {message.channel.name}")
    if message.author.id == client.user.id: return
    if message.channel.id not in CHANNEL_IDS: 
        print(f"DEBUG: Ignored. Channel ID {message.channel.id} is not in the list.")
        return
    if message.author.id != BOT_ID:
        print(f"DEBUG: Ignored. Author ID {message.author.id} does not match {BOT_ID}.")
        return
    text = message.content
    if message.embeds:
        for e in message.embeds:
            if e.title: text += " " + e.title
            if e.description: text += " " + e.description
            if e.footer and e.footer.text: text += " " + e.footer.text
            for field in e.fields:
                text += f" {field.name} {field.value}"

    # If the round ended, clear the active state so we stop retrying
    if "scramble ended" in text.lower():
        if message.channel.id in ACTIVE_SCRAMBLES:
            del ACTIVE_SCRAMBLES[message.channel.id]
            print(f"[*] Scramble ended in {message.channel.name}. Cleared state.")
        return

    scramble = extract_scramble(text)
    
    if scramble and len(scramble) >= 4:
        # Check if we are already trying to solve this exact scramble
        if ACTIVE_SCRAMBLES.get(message.channel.id) == scramble:
            return

        # New scramble detected! Mark it as active and start the solver
        ACTIVE_SCRAMBLES[message.channel.id] = scramble
        print(f"[*] New scramble in {message.channel.name}: {scramble}")
        
        # Create an async task so it runs in the background without blocking
        client.loop.create_task(attempt_solve(message.channel, scramble))

client.run(TOKEN)
