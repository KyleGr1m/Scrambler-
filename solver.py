import os, json, urllib.request, re

TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BOT_ID = os.environ.get("BOT_ID")

def req(url, method="GET", data=None):
    headers = {"Authorization": TOKEN, "User-Agent": "Mozilla/5.0"}
    if data:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error: {e}")
        return None

# 1. Get our own user ID to prevent spamming
me = req("https://discord.com/api/v9/users/@me")
if not me: exit()
MY_ID = me["id"]

# 2. Fetch last 5 messages
msgs = req(f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages?limit=5")
if not msgs: exit()

# 3. Check if we already replied in the last 5 messages
if any(m["author"]["id"] == MY_ID for m in msgs):
    print("We already replied recently. Sleeping.")
    exit()

# 4. Find the scramble
scramble = None
for m in msgs:
    if m["author"]["id"] == BOT_ID:
        content = m.get("content", "")
        if m.get("embeds"):
            for e in m["embeds"]:
                content += " " + str(e.get("title", ""))
                content += " " + str(e.get("description", ""))
        
        if "Scramble ended" in content: continue
        
        caps = re.findall(r'\b[A-Z]{4,}\b', content)
        ignore = ["WORD", "SCRAMBLE", "REWARD", "ENDS", "MINUTES", "TYPE", "CORRECT", "GOOD", "LUCK"]
        valid = [w for w in caps if w not in ignore]
        if valid:
            scramble = max(valid, key=len)
            break

if not scramble:
    print("No active scramble found.")
    exit()

print(f"Found: {scramble}")

# 5. Query Datamuse
r_ana = urllib.request.Request(f"https://api.datamuse.com/words?rel_ana={scramble}", headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(r_ana) as resp:
    data = json.loads(resp.read().decode())
    answers = [item['word'].upper() for item in data if len(item['word']) == len(scramble)]

if not answers:
    print("No answers found.")
    exit()

# 6. Send answer
print(f"Sending: {answers[0]}")
req(f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages", method="POST", data={"content": answers[0]})
