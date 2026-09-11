"""Build the project's original, editable vector identity. No neural data is drawn."""

from pathlib import Path
import math
import base64
import random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
OUT.mkdir(parents=True, exist_ok=True)

DEFS = """
<defs>
  <radialGradient id="halo"><stop stop-color="#458578" stop-opacity=".29"/><stop offset="1" stop-color="#163631" stop-opacity="0"/></radialGradient>
  <linearGradient id="wing" x1="0" y1="1" x2=".8" y2="0"><stop stop-color="#37685e" stop-opacity=".8"/><stop offset=".45" stop-color="#c9e6d3" stop-opacity=".72"/><stop offset=".76" stop-color="#efffed" stop-opacity=".93"/><stop offset="1" stop-color="#548e85" stop-opacity=".36"/></linearGradient>
  <linearGradient id="body" x1="0" y1="0" x2=".3" y2="1"><stop stop-color="#d5b780"/><stop offset=".18" stop-color="#756c4b"/><stop offset=".46" stop-color="#363e31"/><stop offset=".76" stop-color="#202621"/><stop offset="1" stop-color="#101613"/></linearGradient>
  <linearGradient id="thorax" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#b2ba8d"/><stop offset=".3" stop-color="#5b6852"/><stop offset=".68" stop-color="#273d32"/><stop offset="1" stop-color="#0e1a15"/></linearGradient>
  <radialGradient id="eye" cx=".32" cy=".25" r=".8"><stop stop-color="#ffd697"/><stop offset=".24" stop-color="#ff8950"/><stop offset=".65" stop-color="#d94d2c"/><stop offset="1" stop-color="#6e251d"/></radialGradient>
  <linearGradient id="edge"><stop stop-color="#eaf7d3"/><stop offset="1" stop-color="#447362"/></linearGradient>
  <filter id="shadow" x="-70%" y="-70%" width="240%" height="240%"><feDropShadow dx="0" dy="25" stdDeviation="20" flood-color="#000" flood-opacity=".48"/></filter>
  <clipPath id="eyeClip"><ellipse cx="91" cy="-6" rx="34" ry="43" transform="rotate(-22 91 -6)"/></clipPath>
</defs>
"""


def fly():
    # Stylized Drosophila, with one pair of wings and three pairs of legs.
    parts = ["<g stroke-linecap='round' stroke-linejoin='round'>"]
    legs = [
        "M-10-15 -40-76 -77-88 -94-119",
        "M26-13 51-70 89-88 110-121",
        "M61-10 114-60 159-53 181-68",
        "M-12 18 -47 68 -89 81 -112 112",
        "M28 20 42 76 89 88 108 116",
        "M62 16 105 65 151 69 173 97",
    ]
    for path in legs:
        parts.append(f'<path d="{path}" fill="none" stroke="#101c17" stroke-width="6"/>')
        parts.append(f'<path d="{path}" fill="none" stroke="url(#edge)" stroke-width="2"/>')
    parts.append("""
    <path d="M5-14C-33-58-56-144-121-179C-180-211-215-180-191-132C-166-81-73-30 5-6Z" fill="url(#wing)" stroke="#b4d5bd" stroke-width="1.3"/>
    <path d="M3 12C-46 33-69 118-144 145C-206 168-239 136-203 96C-161 50-68 22 3 6Z" fill="url(#wing)" stroke="#96bbaa" stroke-width="1.3"/>
    <g fill="none" stroke="#355c4b" stroke-width="1.15" opacity=".8">
      <path d="M1-12C-76-48-158-113-197-167M-16-23C-88-70-116-133-147-183M-56-52-58-79-84-96-111-100M-99-88-100-119-126-135-151-134M-114-139-146-142-167-166M-154-126-165-112"/>
      <path d="M0 10C-92 29-170 85-220 124M-12 17C-94 57-121 113-173 150M-59 41-74 72-105 85-127 80M-104 85-118 108-142 117-167 107M-147 119-161 139"/>
    </g>
    <g fill="none" stroke="#f0ffe6" stroke-width=".65" opacity=".55">
      <path d="M-3-13C-79-54-147-113-194-168M-3 12C-102 42-167 91-216 126"/>
      <path d="M-72-109-86-124M-86-88-119-90M-135-158-153-164M-89 60-116 63M-165 99-178 105"/>
    </g>
    <path d="M8-22C-26-48-80-46-117-24C-147-6-145 11-114 27C-75 47-24 43 8 22Z" fill="url(#body)" stroke="#627452" stroke-width="1.3"/>
    <g fill="none" stroke="#182b20" stroke-width="9" opacity=".85">
      <path d="M-37-36Q-12 0-38 35M-66-36Q-45 0-66 36M-95-28Q-77 0-97 27M-118-17Q-106 0-118 16"/>
    </g>
    <path d="M-114-22C-77-39-37-37-13-26" stroke="#e9d596" stroke-width="2" opacity=".45" fill="none"/>
    <ellipse cx="24" cy="0" rx="49" ry="37" fill="url(#thorax)" stroke="#6b8262" stroke-width="1.3"/>
    <path d="M-9-20C13-30 36-29 51-16M-6-10C16-18 35-17 48-10" stroke="#d5d6a7" stroke-width="2" fill="none" opacity=".36"/>
    <ellipse cx="77" cy="0" rx="31" ry="35" fill="#354c35" stroke="#788563" stroke-width="1.4"/>
    <ellipse cx="69" cy="-21" rx="20" ry="25" fill="url(#eye)" transform="rotate(-25 69 -21)"/>
    <ellipse cx="91" cy="-6" rx="34" ry="43" transform="rotate(-22 91 -6)" fill="url(#eye)" stroke="#b9613c" stroke-width="1"/>
    <g clip-path="url(#eyeClip)" fill="none" stroke="#762c20" stroke-width=".65" opacity=".4">
    """)
    for row in range(-10, 11):
        for col in range(-8, 9):
            x, y = 91 + col * 6 + (row % 2) * 3, -6 + row * 5.2
            points = " ".join(f"{x + 3.05 * math.cos(math.pi * k / 3):.2f},{y + 3.05 * math.sin(math.pi * k / 3):.2f}" for k in range(6))
            parts.append(f'<polygon points="{points}"/>')
    parts.append("""</g>
    <ellipse cx="83" cy="-27" rx="12" ry="5" fill="#ffe3ac" opacity=".24" transform="rotate(-30 83 -27)"/>
    <path d="M110-25 134-45 151-43M121-8 146-16 162-10" stroke="#a9b989" stroke-width="2" fill="none"/>
    <ellipse cx="135" cy="-45" rx="6" ry="3" fill="#8e9f71" transform="rotate(-25 135 -45)"/>
    <path d="M144-44 152-57M148-46 152-51M149-52 157-54M144-17 158-25M150-20 153-28" stroke="#a9b989" stroke-width=".8" fill="none"/>
    <path d="M114 18 135 31 128 42" stroke="#4f6445" stroke-width="2" fill="none"/>
    """)
    rng = random.Random(12)
    for _ in range(88):
        theta = rng.uniform(0, math.tau)
        x, y = 24 + math.cos(theta) * rng.uniform(20, 46), math.sin(theta) * rng.uniform(18, 35)
        parts.append(f'<path d="M{x:.1f} {y:.1f}l{-rng.uniform(3,8):.1f} {-rng.uniform(1,5):.1f}" stroke="#b8c18d" stroke-width=".65" opacity=".6"/>')
    parts.append("</g>")
    return "".join(parts)


FLY = fly()


def svg(body, width, height, title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title"><title id="title">{title}</title>{DEFS}{body}</svg>\n'


hero = """
<ellipse cx="330" cy="302" rx="303" ry="280" fill="url(#halo)"/>
<g fill="none" stroke="#567366" stroke-width=".8">
  <circle cx="325" cy="292" r="222" opacity=".33"/>
  <circle cx="325" cy="292" r="253" stroke-dasharray="1 10" opacity=".65"/>
  <path d="M65 292H91M559 292H585M325 32V59M325 523V551" opacity=".75"/>
  <ellipse cx="325" cy="292" rx="264" ry="91" transform="rotate(-29 325 292)" opacity=".33"/>
</g>
<g fill="#789887" font-family="monospace" font-size="9" letter-spacing="2">
  <text x="314" y="17">00°</text><text x="574" y="281">90°</text>
  <text x="55" y="281">270°</text><text x="310" y="574">180°</text>
</g>
"""
hero += '<g transform="translate(361 303) rotate(-24) scale(1.33)" filter="url(#shadow)">' + FLY + '</g>'
hero += """
<g fill="none" stroke="#8b9c80" stroke-width=".8"><path d="M439 241 512 186H604"/><circle cx="439" cy="241" r="3" fill="#ff885c" stroke="none"/><path d="M276 343 178 441H36"/><circle cx="276" cy="343" r="3" fill="#becdae" stroke="none"/></g>
<g font-family="monospace" font-size="10" letter-spacing="1.1"><text x="513" y="174" fill="#d3dbc6">FRUIT FLY</text><text x="36" y="462" fill="#8fa28e">SMALL BY DESIGN.</text></g>
"""
(OUT / "fly-specimen.svg").write_text(svg(hero, 650, 590, "An original illustration of a fruit fly with translucent wings and amber compound eyes."))

mark = '<rect width="80" height="80" rx="22" fill="#ff805c"/><g fill="#14211a" transform="translate(40 40) rotate(-28)"><ellipse cx="0" cy="10" rx="6" ry="16"/><ellipse cx="-11" cy="-6" rx="7" ry="17" transform="rotate(-33 -11 -6)"/><ellipse cx="11" cy="-6" rx="7" ry="17" transform="rotate(33 11 -6)"/><circle cy="-9" r="7"/></g>'
(OUT / "mark.svg").write_text(svg(mark, 80, 80, "Flappy Fly"))

font = base64.b64encode((OUT / 'fonts/BarlowCondensed-ExtraBold.ttf').read_bytes()).decode()
banner = f'<style>@font-face{{font-family:Barlow;src:url(data:font/ttf;base64,{font})}}text.display{{font-family:Barlow,sans-serif;font-weight:800}}</style>'
banner += '<rect width="1280" height="560" fill="#101712"/><path d="M36 87H1244M36 505H1244" stroke="#334036"/>'
banner += '<g font-family="Arial,Helvetica,sans-serif"><text x="40" y="55" fill="#f0f1e6" font-size="22" font-weight="700">flappy fly<tspan fill="#ff805c">.</tspan></text><text x="1238" y="54" text-anchor="end" fill="#9fa995" font-family="monospace" font-size="12" letter-spacing="2">AN OPEN NEUROSCIENCE ARCADE</text><text x="43" y="158" fill="#ff9878" font-family="monospace" font-size="12" letter-spacing="3">REAL FLY WIRING. ONE BUTTON.</text><text x="36" y="266" class="display" fill="#f0f1e6" font-size="128" letter-spacing="-1">TINY BRAIN.</text><text x="36" y="378" class="display" fill="#ff805c" font-size="146" letter-spacing="-1">BIG FLAP.</text><text x="42" y="426" fill="#abb5a4" font-size="19">166,700 neurons meet Flappy Bird.</text><text x="42" y="467" fill="#cfddbb" font-family="monospace" font-size="12" letter-spacing="2">PLAY · EXPERIMENT · REPEAT</text><text x="41" y="536" fill="#a4b195" font-family="monospace" font-size="12">FULL MAP VERIFIED</text><circle cx="227" cy="532" r="3" fill="#b7cd90"/><text x="250" y="536" fill="#a4b195" font-family="monospace" font-size="12">FIRST DECODER PILOTS RECORDED</text></g>'
banner += '<g transform="translate(620 -8) scale(.87)">' + hero + '</g>'
(OUT / "readme-hero.svg").write_text(svg(banner, 1280, 560, "Flappy Fly. Tiny brain. Big flap. An open neuroscience arcade."))
(OUT / "social-card.svg").write_text(svg('<rect width="1280" height="672" fill="#101712"/><g transform="translate(0 56)">' + banner + '</g>', 1280, 672, "Flappy Fly — 166,700 neurons meet Flappy Bird."))

parts = ['<rect width="1280" height="210" fill="#101712"/>']
for i, (name, detail) in enumerate([("Game pixels", "A visual observation"), ("Retinal adapter", "A modeled projection"), ("Full fly network", "Mapped weights stay fixed"), ("Action decoder", "Learns flap or wait")]):
    x = 32 + i * 312
    parts.append(f'<path d="M{x} 31h280" stroke="{"#ff805c" if i == 3 else "#5c7054"}"/><text x="{x}" y="70" fill="#ff9878" font-family="monospace" font-size="15">0{i+1}</text><text x="{x}" y="113" fill="#eef1e2" font-family="Arial,sans-serif" font-size="25" font-weight="700">{name}</text><text x="{x}" y="145" fill="#a4b195" font-family="Arial,sans-serif" font-size="16">{detail}</text>')
    if i < 3:
        parts.append(f'<path d="M{x+261} 68h19m-5-5 5 5-5 5" fill="none" stroke="#a4b195" stroke-width="1.5"/>')
(OUT / "pipeline.svg").write_text(svg("".join(parts), 1280, 210, "Game pixels, a retinal adapter, the fixed full fly network, and a trainable action decoder."))
print("Generated five original vector assets.")
