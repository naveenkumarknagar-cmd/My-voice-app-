import asyncio
import io

import edge_tts
from flask import Flask, render_template_string, request, send_file

app = Flask(__name__)

VOICES = [
    ("hi-IN-MadhurNeural", "Hindi - Madhur (male)"),
    ("hi-IN-SwaraNeural", "Hindi - Swara (female)"),
    ("en-IN-PrabhatNeural", "English India - Prabhat (male)"),
    ("en-IN-NeerjaNeural", "English India - Neerja (female)"),
    ("en-US-GuyNeural", "English US - Guy (male)"),
    ("en-US-AriaNeural", "English US - Aria (female)"),
]

PAGE = """<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kahani Awaaz</title>
<style>
  :root { --bg:#14172b; --card:#1d2140; --ink:#f3ecdc; --mute:#9aa0c4; --gold:#f2b84b; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-family: Georgia, 'Noto Serif Devanagari', serif; padding:16px; }
  main { max-width:640px; margin:0 auto; }
  h1 { font-size:1.7rem; margin:8px 0 4px; }
  p.sub { color:var(--mute); margin:0 0 16px; font-family: system-ui, sans-serif; font-size:.95rem; }
  label { display:block; margin:14px 0 6px; font-family: system-ui, sans-serif; font-size:.9rem; color:var(--mute); }
  textarea, select { width:100%; background:var(--card); color:var(--ink); border:1px solid #333a6b; border-radius:10px; padding:12px; font-size:1rem; font-family:inherit; }
  textarea { min-height:220px; resize:vertical; line-height:1.5; }
  input[type=range] { width:100%; accent-color:var(--gold); }
  button { width:100%; margin-top:18px; padding:14px; border:0; border-radius:10px; background:var(--gold); color:#2a1f05; font-size:1.05rem; font-weight:700; }
  button:disabled { opacity:.6; }
  #out { margin-top:18px; display:none; }
  audio { width:100%; }
  a.dl { display:block; margin-top:10px; text-align:center; padding:12px; border:1px solid var(--gold); border-radius:10px; color:var(--gold); text-decoration:none; font-family: system-ui, sans-serif; }
  #err { color:#ff9b9b; margin-top:12px; font-family: system-ui, sans-serif; }
</style>
</head>
<body>
<main>
  <h1>Kahani Awaaz</h1>
  <p class="sub">Kahani paste karo, awaaz chuno, MP3 download karo.</p>

  <label for="text">Kahani ka text</label>
  <textarea id="text" placeholder="Yahan apni kahani likho ya paste karo..."></textarea>

  <label for="voice">Awaaz</label>
  <select id="voice">
    {% for v, name in voices %}<option value="{{ v }}">{{ name }}</option>{% endfor %}
  </select>

  <label for="rate">Speed: <span id="rv">-10</span>% (kahani ke liye thodi dheemi)</label>
  <input id="rate" type="range" min="-40" max="30" value="-10">

  <label for="pitch">Pitch: <span id="pv">-4</span>Hz (kam = gehri awaaz)</label>
  <input id="pitch" type="range" min="-30" max="30" value="-4">

  <button id="go">Awaaz banao</button>
  <div id="err"></div>

  <div id="out">
    <audio id="player" controls></audio>
    <a id="dl" class="dl" download="kahani.mp3">MP3 download karo</a>
  </div>
</main>
<script>
const $ = id => document.getElementById(id);
$('rate').oninput = () => $('rv').textContent = $('rate').value;
$('pitch').oninput = () => $('pv').textContent = $('pitch').value;

$('go').onclick = async () => {
  const text = $('text').value.trim();
  $('err').textContent = '';
  if (!text) { $('err').textContent = 'Pehle kahani ka text daalo.'; return; }
  $('go').disabled = true; $('go').textContent = 'Ban rahi hai...';
  try {
    const r = await fetch('/tts', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, voice: $('voice').value, rate: +$('rate').value, pitch: +$('pitch').value})
    });
    if (!r.ok) throw new Error(await r.text());
    const url = URL.createObjectURL(await r.blob());
    $('player').src = url; $('dl').href = url;
    $('out').style.display = 'block';
    $('player').play();
  } catch (e) {
    $('err').textContent = 'Error: ' + e.message;
  } finally {
    $('go').disabled = false; $('go').textContent = 'Awaaz banao';
  }
};
</script>
</body>
</html>"""


async def synth(text, voice, rate, pitch):
    buf = io.BytesIO()
    comm = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz")
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf


@app.get("/")
def index():
    return render_template_string(PAGE, voices=VOICES)


@app.post("/tts")
def tts():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    voice = data.get("voice")
    if not text or voice not in dict(VOICES):
        return "Text ya voice galat hai.", 400
    try:
        buf = asyncio.run(synth(text, voice, int(data.get("rate", -10)), int(data.get("pitch", -4))))
    except Exception as e:
        return f"Voice banane mein dikkat: {e}", 500
    return send_file(buf, mimetype="audio/mpeg", download_name="kahani.mp3")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
