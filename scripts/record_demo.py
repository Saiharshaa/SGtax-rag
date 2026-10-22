"""Record a narrated, captioned demo video of the app: results/demo.mp4 (+ results/demo_script.md).

    python scripts/record_demo.py              # narrated with a Windows voice (Microsoft Zira)
    python scripts/record_demo.py --no-voice   # captions only, e.g. to record your own voice over it

Starts the app on localhost with a demo password and drives it in a headless browser like a user would.
Each scene shows a caption and is held until its narration has been spoken; the seconds spent waiting
for answers are cut, and the narration clips are laid over the cut video at the matching times.
Needs the dev extras: pip install playwright imageio-ffmpeg && python -m playwright install chromium.
The voice uses Windows' built-in speech (System.Speech); elsewhere, use --no-voice.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT, SCRIPT_OUT = ROOT / "results" / "demo.mp4", ROOT / "results" / "demo_script.md"
PORT, PASSWORD, VOICE = 8599, "demo-only-password", "Microsoft Zira Desktop"
SIZE = {"width": 1280, "height": 800}
SPINNER = "Searching the Act and the e-Tax guides"
CHAT_INPUT = "Ask a Singapore corporate income tax question"
EXAMPLE = "Can a company deduct expenses it incurred before it started its business?"

# Results shown on the end card and read out at the end (from results/metrics.md).
RESULTS = {"naive_recall": "0.67", "structured_recall": "0.81", "naive_mrr": "0.62", "structured_mrr": "0.80",
           "naive_exact": "0%", "structured_exact": "100%", "naive_refused": "3 / 3", "structured_refused": "3 / 3"}
SPOKEN_RESULTS = ("81 percent of the right sources, against 67 percent for naive chunks searched the same way, "
                  "and ranked them higher")

# scene: (caption shown on screen, narration spoken)
SCENES = {
    "intro": ("Cited answers to Singapore corporate income tax questions, from the Income Tax Act 1947 and five "
              "IRAS e-Tax guides.",
              "This is our retrieval-augmented assistant for Singapore corporate income tax. It answers questions "
              "from the Income Tax Act 1947 and five IRAS e-Tax guides, and cites a section or paragraph for every "
              "statement."),
    "password": ("Password-protected: the index holds the text of the IRAS guides.",
                 "The app is password protected, because its index holds the text of the IRAS guides."),
    "landing": ("Built for tax associates at SME-focused accounting firms. Start from an example, or ask your own.",
                "It is built for tax associates at small and medium-sized accounting firms. You can start from an "
                "example, or ask your own question."),
    "search": ("Search: Gemini embeddings over chunks that follow the Act's subsections and the guides' paragraphs.",
               "The question is embedded with Gemini and matched against chunks that follow the structure of the "
               "law: one chunk for each subsection of the Act, and one for each paragraph of a guide."),
    "citations": ("Every statement carries a citation such as [ITA 1947, s 14R(2)]. The model cites numbered "
                  "sources and the code turns them into citations, so it can't invent one.",
                  "Every statement in the answer carries a citation. The model cites numbered sources, and our code "
                  "turns each number into a legal citation, such as section 14R, subsection 2, of the Income Tax "
                  "Act. So a citation can only point at a source the model was actually shown."),
    "sources": ("Sources open as short excerpts, never whole documents.",
                "The cited sources open as short excerpts, so an associate can check each citation in seconds."),
    "section": ("When a question names a section, keyword search (BM25) and a section boost join in.",
                "When a question names a section, keyword search and a section boost join the semantic search, "
                "because exact section numbers are where embeddings are weakest."),
    "section_result": ("The named section comes first, with the e-Tax guide paragraphs that explain it.",
                       "The named section, 37D subsection 3, comes first, together with the guide paragraphs that "
                       "explain it."),
    "refuse": ("Questions the Act and guides don't cover are refused, not guessed.",
               "If the Act and the guides don't cover a question, the assistant refuses instead of guessing. Here we "
               "ask about the GST rate, which is outside our sources."),
    "refused": ("Refused: the sources don't answer it.", "It declines, and says why."),
    "compare": ("Compare: the same model given naive 500-token chunks, the approach this project measures against.",
                "Finally, we compare against a naive baseline: the same model, given plain 500-token chunks "
                "without any legal structure."),
    "structured_answer": ("Structure-aware: cites the Act (s 37D) and the exact e-Tax guide paragraphs.",
                          "Our structure-aware version cites both the Act, section 37D, and the exact paragraphs "
                          "of the carry-back guide."),
    "naive_answer": ("Naive baseline: its chunks have no section or paragraph, so it can only cite the whole guide.",
                     "The naive baseline can only cite the whole guide, because its chunks have no section or "
                     "paragraph numbers."),
    "end": ("", f"On twenty-five test questions with known answers, with the same Gemini search and the same "
                f"amount of context, structure-aware chunks found {SPOKEN_RESULTS}. And every citation names an "
                f"exact section or paragraph. Thank you for watching."),
}
END_CARD = """
<h2>Does the structure help? Measured on 25 questions with gold sections and paragraphs</h2>
<table>
<tr><th></th><th>Naive 500-token chunks</th><th>Structure-aware chunks</th></tr>
<tr><td colspan="3" style="color:#52514e">Both searched with the same Gemini embeddings</td></tr>
<tr><td>Right sources found, same amount of context</td><td>{naive_recall}</td><td><b>{structured_recall}</b></td></tr>
<tr><td>How high the first right source ranks (MRR)</td><td>{naive_mrr}</td><td><b>{structured_mrr}</b></td></tr>
<tr><td>Citations naming an exact section or paragraph</td><td>{naive_exact}</td><td><b>{structured_exact}</b></td></tr>
<tr><td>Out-of-scope questions refused</td><td>{naive_refused}</td><td>{structured_refused}</td></tr>
</table>
<p>Full results, method and caveats: results/metrics.md and docs/PLAN.md</p>
"""


def synthesize(folder: Path) -> dict[str, Path]:
    """One WAV per scene, spoken by Windows' built-in voice."""
    paths = {name: folder / f"{name}.wav" for name in SCENES}
    quote = lambda text: "'" + text.replace("'", "''") + "'"
    lines = ["Add-Type -AssemblyName System.Speech",
             "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
             f"$s.SelectVoice({quote(VOICE)})", "$s.Rate = 0"]
    for name, (_, speech) in SCENES.items():
        lines += [f"$s.SetOutputToWaveFile({quote(str(paths[name]))})", f"$s.Speak({quote(speech)})"]
    lines.append("$s.Dispose()")
    script = folder / "speak.ps1"
    script.write_text("\n".join(lines), encoding="utf-8-sig")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=True)
    return paths


def duration(wav: Path) -> float:
    with wave.open(str(wav)) as f:
        return f.getnframes() / f.getframerate()


class Recorder:
    """Drives the page, holds each scene for its narration, and remembers the stretches to cut."""

    def __init__(self, page: Page, voice: dict[str, Path] | None):
        self.page, self.voice, self.started = page, voice, time.monotonic()
        self.cuts: list[tuple[float, float]] = []
        self.spoken: list[tuple[str, float]] = []   # (scene, start time in the raw video)

    def now(self) -> float:
        return time.monotonic() - self.started

    def say(self, scene: str, hold: float = 2.5) -> None:
        """Show the scene's caption and hold until its narration (or `hold` seconds) is over."""
        caption = SCENES[scene][0]
        if caption:
            self.page.evaluate("""text => {
                let el = document.getElementById('demo-caption');
                if (!el) {
                    el = document.createElement('div');
                    el.id = 'demo-caption';
                    el.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;padding:18px 32px;' +
                        'background:rgba(11,11,11,0.86);color:#fcfcfb;font:500 21px/1.4 system-ui,sans-serif;';
                    document.body.appendChild(el);
                }
                el.textContent = text;
            }""", caption)
        self.spoken.append((scene, self.now()))
        seconds = duration(self.voice[scene]) + 0.6 if self.voice else hold
        self.page.wait_for_timeout(seconds * 1000)

    def end_card(self, html: str) -> None:
        self.page.evaluate("""html => {
            const el = document.createElement('div');
            el.style.cssText = 'position:fixed;inset:0;z-index:100000;background:#fcfcfb;color:#0b0b0b;' +
                'font:18px/1.5 system-ui,sans-serif;padding:72px 96px;';
            el.innerHTML = html + '<style>table{border-collapse:collapse;margin:28px 0;font-size:20px}' +
                'td,th{padding:12px 22px;border-bottom:1px solid #e4e3df;text-align:left}p{color:#52514e}</style>';
            document.body.appendChild(el);
        }""", html)
        self.say("end", hold=8)
        self.page.wait_for_timeout(1500)

    def scroll_down(self) -> None:
        self.page.evaluate("""() => {
            const main = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
            main.scrollTo({top: main.scrollHeight, behavior: 'smooth'});
        }""")
        self.page.wait_for_timeout(1200)

    def show_last(self, selector: str) -> None:
        """Scroll the last element matching selector to the top of the view (the newest answer's tabs)."""
        self.page.evaluate("""selector => {
            const all = document.querySelectorAll(selector);
            if (all.length) all[all.length - 1].scrollIntoView({block: 'start', behavior: 'smooth'});
        }""", selector)
        self.page.wait_for_timeout(1200)

    def wait_for_answer(self) -> None:
        """Wait out the spinner, cutting all but the first second of it from the video."""
        spinner = self.page.get_by_text(SPINNER)
        spinner.first.wait_for(state="visible", timeout=15_000)
        cut_from = self.now() + 1.0
        spinner.first.wait_for(state="hidden", timeout=240_000)
        self.page.wait_for_timeout(3000)   # the app redraws once the answer is saved
        self.cuts.append((cut_from, self.now() - 0.5))
        self.scroll_down()

    def ask(self, question: str) -> None:
        box = self.page.get_by_placeholder(CHAT_INPUT)
        box.click()
        box.press_sequentially(question, delay=30)
        box.press("Enter")
        self.wait_for_answer()

    def cut_time(self, t: float) -> float:
        """Where raw time t lands once the cuts are removed."""
        return t - sum(min(end, t) - start for start, end in self.cuts if start < t)


def walkthrough(rec: Recorder) -> None:
    page = rec.page
    page.goto(f"http://127.0.0.1:{PORT}")
    page.get_by_label("Password", exact=True).wait_for(timeout=60_000)
    rec.say("intro")
    rec.say("password")
    page.get_by_label("Password", exact=True).press_sequentially(PASSWORD, delay=25)
    page.get_by_role("button", name="Sign in").click()
    page.get_by_placeholder(CHAT_INPUT).wait_for(timeout=60_000)
    rec.say("landing")

    rec.say("search")
    page.get_by_role("button", name=EXAMPLE).click()
    rec.wait_for_answer()
    rec.say("citations")
    page.get_by_text("Sources cited").last.click()
    rec.scroll_down()
    rec.say("sources")

    rec.say("section")
    rec.ask("What does s 37D(3) say about the amount that can be carried back?")
    rec.say("section_result")

    rec.say("refuse")
    rec.ask("What GST rate must a GST-registered company charge on standard-rated supplies?")
    rec.say("refused")

    page.get_by_text("Compare with the naive baseline").click()
    rec.say("compare")
    rec.ask("By when must a company elect to carry back this year's loss against last year's income, "
            "and can it withdraw the election afterwards?")
    rec.show_last('[data-testid="stTabs"]')
    rec.say("structured_answer")
    page.get_by_role("tab", name="Naive baseline").last.click()
    page.wait_for_timeout(800)
    rec.show_last('[data-testid="stTabs"]')
    rec.say("naive_answer")
    rec.end_card(END_CARD.format(**RESULTS))


def start_app() -> subprocess.Popen:
    env = {**os.environ, "APP_PASSWORD": PASSWORD}
    app = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(PORT),
                            "--server.address", "127.0.0.1", "--server.headless", "true",
                            "--browser.gatherUsageStats", "false", "--client.toolbarMode", "minimal"],
                           cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/_stcore/health", timeout=2)
            return app
        except OSError:
            time.sleep(1)
    app.terminate()
    raise RuntimeError("the app did not start")


def render(raw: Path, rec: Recorder, voice: dict[str, Path] | None, out: Path) -> None:
    """Cut the waits out of the raw recording and, with a voice, lay each narration clip at its scene."""
    cut = "+".join(f"between(t,{start:.2f},{end:.2f})" for start, end in rec.cuts if end > start) or "0"
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(raw)]
    video = f"[0:v]select='not({cut})',setpts=N/FRAME_RATE/TB[v]"
    if voice:
        clips = [(scene, rec.cut_time(start)) for scene, start in rec.spoken]
        for scene, _ in clips:
            command += ["-i", str(voice[scene])]
        delays = ";".join(f"[{i + 1}:a]adelay={int(at * 1000)}:all=1[a{i}]" for i, (_, at) in enumerate(clips))
        mix = "".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0[a]"
        command += ["-filter_complex", f"{video};{delays};{mix}", "-map", "[v]", "-map", "[a]",
                    "-c:a", "aac", "-b:a", "160k"]
    else:
        command += ["-filter_complex", video, "-map", "[v]", "-an"]
    command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", str(out)]
    out.parent.mkdir(exist_ok=True)
    subprocess.run(command, check=True)


def write_script(rec: Recorder, out: Path) -> None:
    """The narration with timestamps in the final video, for reading along or recording your own voice."""
    lines = ["# Demo video script", "", f"Narration of `{OUT.name}`, with where each line starts in the video.", ""]
    for scene, start in rec.spoken:
        at = rec.cut_time(start)
        lines.append(f"**{int(at // 60)}:{int(at % 60):02d}** {SCENES[scene][1]}")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-voice", action="store_true", help="captions only, no narration")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as work:
        voice = None if args.no_voice else synthesize(Path(work))
        app = start_app()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(viewport=SIZE, record_video_dir=work, record_video_size=SIZE)
                page = context.new_page()
                rec = Recorder(page, voice)
                try:
                    walkthrough(rec)
                finally:
                    context.close()      # the video file is written on close
                    raw = Path(page.video.path())
                    browser.close()
        finally:
            app.terminate()
        render(raw, rec, voice, OUT)
        write_script(rec, SCRIPT_OUT)
    print(f"wrote {OUT} and {SCRIPT_OUT}")


if __name__ == "__main__":
    main()
