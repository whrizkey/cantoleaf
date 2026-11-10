import asyncio
import importlib.util
import shutil
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from cantoleaf import __version__
from cantoleaf.config import get_settings
from cantoleaf.export.lyrics import export_lrc, export_srt
from cantoleaf.export.m4b import master_m4b_audiobook
from cantoleaf.export.vault import export_obsidian_marginalia
from cantoleaf.ingest.registry import load_document
from cantoleaf.models import DepthGear, LangMode, SynthesizedSpan, Utterance
from cantoleaf.pipeline.accounting import UsageTracker
from cantoleaf.pipeline.cache import AudioCache
from cantoleaf.pipeline.synthesizer import SynthesisPipeline
from cantoleaf.providers.registry import get_adapt_provider, get_tts_provider
from cantoleaf.workflows.bilingual_bridge import weave_bilingual_stream
from cantoleaf.workflows.depth_gears import generate_depth_stream

app = typer.Typer(
    name="cantoleaf",
    help="CantoLeaf: Cognitive audio reader and audiobook studio.",
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print the current CantoLeaf version."""
    console.print(f"[bold green]CantoLeaf[/bold green] version [cyan]{__version__}[/cyan]")


@app.command()
def doctor() -> None:
    """Check system dependencies, audio tools, and configured provider readiness."""
    console.print("\n[bold cyan]CantoLeaf System Diagnostics[/bold cyan]")
    console.print("[dim]-------------------------------------[/dim]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="dim", width=24)
    table.add_column("Status", width=14)
    table.add_column("Details")

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python Runtime", "[green]OK[/green]", f"Python {py_ver}")

    # ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        table.add_row("ffmpeg", "[green]OK[/green]", ffmpeg_path)
    else:
        table.add_row(
            "ffmpeg", "[yellow]MISSING[/yellow]", "Install ffmpeg for audio mastering & m4b export"
        )

    # ffprobe
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        table.add_row("ffprobe", "[green]OK[/green]", ffprobe_path)
    else:
        table.add_row("ffprobe", "[yellow]MISSING[/yellow]", "Install ffprobe for audio analysis")

    # Optional extra: edge-tts
    has_edge = importlib.util.find_spec("edge_tts") is not None
    table.add_row(
        "Edge TTS Package",
        "[green]INSTALLED[/green]" if has_edge else "[yellow]OPTIONAL[/yellow]",
        "Built-in zero-key TTS engine" if has_edge else "Install with: pip install cantoleaf[tts]",
    )

    settings = get_settings()

    # TTS provider status
    table.add_row(
        "Default TTS Provider",
        "[cyan]CONFIGURED[/cyan]",
        f"{settings.cantoleaf_tts_provider} (voice: {settings.cantoleaf_tts_voice})",
    )

    # Cloud API Keys
    table.add_row(
        "ElevenLabs API Key",
        "[green]CONFIGURED[/green]" if settings.elevenlabs_api_key else "[dim]NOT SET[/dim]",
        f"Model: {settings.elevenlabs_model_id}"
        if settings.elevenlabs_api_key
        else "BYOK optional",
    )
    table.add_row(
        "OpenAI API Key",
        "[green]CONFIGURED[/green]" if settings.openai_api_key else "[dim]NOT SET[/dim]",
        f"Base URL: {settings.openai_base_url}" if settings.openai_api_key else "BYOK optional",
    )

    # Budget cap
    pricing_exists = Path("pricing.toml").exists()
    if settings.cantoleaf_max_cost_usd > 0:
        p_status = "pricing.toml active" if pricing_exists else "default pricing"
        table.add_row(
            "Spend Protection Cap",
            "[green]ACTIVE[/green]",
            f"${settings.cantoleaf_max_cost_usd:.2f} max USD ({p_status})",
        )
    else:
        table.add_row(
            "Spend Protection Cap",
            "[yellow]DISABLED[/yellow]",
            "Unlimited (CANTOLEAF_MAX_COST_USD <= 0)",
        )

    console.print(table)
    console.print("")


@app.command()
def estimate(
    file_path: str = typer.Argument(..., help="Path to eBook (.epub), PDF, or Markdown file"),
) -> None:
    """Inspect a document's chapters, block classification, and estimated duration per Depth Gear."""
    try:
        book = load_document(file_path)
    except Exception as e:
        console.print(f"[bold red]Error loading document:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    console.print(f"\n[bold green]{book.title}[/bold green] by [cyan]{book.author}[/cyan]")
    console.print(
        f"Total Chapters: [bold]{len(book.chapters)}[/bold] | Language: [dim]{book.language}[/dim]\n"
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Chapter", style="dim", width=8)
    table.add_column("Title", width=30)
    table.add_column("Blocks", justify="right", width=8)
    table.add_column("Characters", justify="right", width=12)
    table.add_column("Pulse (~10%)", justify="right", width=14)
    table.add_column("Crux (~55%)", justify="right", width=14)
    table.add_column("Verbatim (100%)", justify="right", width=16)

    total_chars = 0
    for ch in book.chapters:
        total_chars += ch.estimated_chars
        v_min = ch.estimated_chars / 900.0
        c_min = v_min * 0.55
        p_min = v_min * 0.10

        table.add_row(
            f"#{ch.index + 1}",
            ch.title[:28] + ("..." if len(ch.title) > 28 else ""),
            str(len(ch.blocks)),
            f"{ch.estimated_chars:,}",
            f"{p_min:.1f} min",
            f"{c_min:.1f} min",
            f"{v_min:.1f} min",
        )

    console.print(table)

    total_v_min = total_chars / 900.0
    console.print(f"\n[bold]Total Book Characters:[/bold] {total_chars:,}")
    console.print(f"• [bold]Gear 1 (Pulse):[/bold] ~{total_v_min * 0.10:.1f} minutes")
    console.print(f"• [bold]Gear 2 (Crux):[/bold] ~{total_v_min * 0.55:.1f} minutes")
    console.print(
        f"• [bold]Gear 3 (Verbatim):[/bold] ~{total_v_min:.1f} minutes ({total_v_min / 60:.1f} hours)\n"
    )


@app.command()
def convert(
    file_path: str = typer.Argument(..., help="Path to eBook (.epub), PDF, or Markdown file"),
    output: str = typer.Option("", "-o", "--output", help="Path to output .m4b audiobook file"),
    gear: str = typer.Option(
        "verbatim", "-g", "--gear", help="Depth gear: pulse | crux | verbatim"
    ),
    provider: str = typer.Option(
        "", "-p", "--provider", help="TTS provider: edge | elevenlabs | fake | openai"
    ),
    voice: str = typer.Option("", "-v", "--voice", help="TTS Voice ID or name"),
    lang_mode: str = typer.Option(
        "source", "-l", "--lang-mode", help="Language mode: source | echo | code_switch"
    ),
    target_lang: str = typer.Option(
        "en", "-t", "--target-lang", help="Target language code (e.g. id, es)"
    ),
    cover: str = typer.Option("", "-c", "--cover", help="Optional cover art image path"),
    export_notes: bool = typer.Option(
        False, "-n", "--notes", help="Export crystallized marginalia notes"
    ),
    vault_dir: str = typer.Option("./notes", "--vault-dir", help="Directory for marginalia notes"),
) -> None:
    """Batch convert an entire eBook into a chaptered .m4b cognitive audiobook."""

    async def _run() -> None:
        try:
            book = load_document(file_path)
        except Exception as e:
            console.print(f"[bold red]Failed to load document:[/bold red] {e}")
            raise typer.Exit(code=1) from e

        settings = get_settings()
        tts_name = provider or settings.cantoleaf_tts_provider.value
        tts = get_tts_provider(tts_name)
        adapt = get_adapt_provider(settings.cantoleaf_adapt_provider.value)
        cache = AudioCache()
        tracker = UsageTracker(max_budget_usd=settings.cantoleaf_max_cost_usd)
        pipeline = SynthesisPipeline(tts, cache, tracker)

        chosen_gear = (
            DepthGear(gear.lower())
            if gear.lower() in DepthGear._value2member_map_
            else DepthGear.VERBATIM
        )
        chosen_mode = (
            LangMode(lang_mode.lower())
            if lang_mode.lower() in LangMode._value2member_map_
            else LangMode.SOURCE
        )

        # Resolve voice default: only use ChristopherNeural if provider is edge
        chosen_voice = voice or (settings.cantoleaf_tts_voice if tts_name == "edge" else None)

        console.print(f"\n[bold green]Converting '{book.title}'[/bold green]")
        console.print(
            f"Gear: [cyan]{chosen_gear.value}[/cyan] | TTS: [cyan]{tts.name}[/cyan] | Chapters: [bold]{len(book.chapters)}[/bold]\n"
        )

        all_spans: list[SynthesizedSpan] = []
        all_utterances: list[Utterance] = []
        chapter_markers: list[tuple[str, float, float]] = []
        cursor_s = 0.0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as prog:
            task = prog.add_task("Synthesizing chapters...", total=len(book.chapters))

            for ch in book.chapters:
                prog.update(task, description=f"Synthesizing: {ch.title[:30]}")
                ch_start = cursor_s
                utterances = await generate_depth_stream(
                    book.book_id, ch, chosen_gear, chosen_mode, adapt
                )
                if chosen_mode != LangMode.SOURCE:
                    utterances = await weave_bilingual_stream(
                        utterances, chosen_mode, target_lang, adapt
                    )

                ch_spans: list[SynthesizedSpan] = []
                for u in utterances:
                    span = await pipeline.synthesize_utterance(u, voice=chosen_voice)
                    ch_spans.append(span)
                    all_spans.append(span)
                    all_utterances.append(u)
                    cursor_s += span.duration_sec + span.pause_after_sec

                chapter_markers.append((ch.title, ch_start, cursor_s))

                if export_notes:
                    from cantoleaf.models import BlockKind

                    if chosen_gear == DepthGear.PULSE:
                        notes_u = utterances
                    else:
                        notes_u = [
                            u
                            for u in utterances
                            if u.block_kind
                            in (BlockKind.QUOTE, BlockKind.RECALL_LOCK, BlockKind.HEADING)
                            or u.voice_role == "margin_whisper"
                        ]
                    if notes_u:
                        export_obsidian_marginalia(
                            book.title, book.author, ch.title, notes_u, Path(vault_dir)
                        )

                prog.advance(task)

        # Output file paths
        out_path = (
            Path(output) if output else Path(f"{Path(file_path).stem}_{chosen_gear.value}.m4b")
        )
        cover_path = Path(cover) if cover else book.cover_image

        console.print("[dim]Mastering .M4B with ffmpeg concat and embedded chapters...[/dim]")
        mastered = master_m4b_audiobook(
            all_spans,
            chapter_markers,
            out_path,
            book_title=book.title,
            author=book.author,
            cover_image=cover_path,
        )

        # Export subtitles with real spoken text
        lrc_path = out_path.with_suffix(".lrc")
        srt_path = out_path.with_suffix(".srt")
        export_lrc(all_spans, lrc_path, book.title, book.author)
        export_srt(all_spans, srt_path, [u.spoken_text for u in all_utterances])

        console.print("\n[bold green]✓ Conversion Complete![/bold green]")
        console.print(f"• Audiobook: [bold cyan]{mastered}[/bold cyan] ({cursor_s / 60:.1f} mins)")
        console.print(f"• Subtitles: {lrc_path.name}, {srt_path.name}")
        console.print(
            f"• Tracked Cost: [bold]${tracker.total_cost_usd:.4f}[/bold] / ${tracker.max_budget_usd:.2f}\n"
        )

    asyncio.run(_run())


@app.command()
def listen(
    file_path: str = typer.Argument(..., help="Path to eBook (.epub), PDF, or Markdown file"),
    chapter: int = typer.Option(
        1, "-c", "--chapter", help="Chapter number to listen to (1-indexed)"
    ),
    gear: str = typer.Option(
        "verbatim", "-g", "--gear", help="Depth gear: pulse | crux | verbatim"
    ),
    provider: str = typer.Option(
        "", "-p", "--provider", help="TTS provider: edge | elevenlabs | fake | openai"
    ),
    voice: str = typer.Option("", "-v", "--voice", help="TTS Voice ID or name"),
) -> None:
    """Synthesize and inspect audio spans for an individual chapter."""

    async def _run() -> None:
        book = load_document(file_path)
        ch_idx = max(0, min(chapter - 1, len(book.chapters) - 1))
        ch = book.chapters[ch_idx]

        settings = get_settings()
        tts_name = provider or settings.cantoleaf_tts_provider.value
        tts = get_tts_provider(tts_name)
        adapt = get_adapt_provider(settings.cantoleaf_adapt_provider.value)
        chosen_gear = (
            DepthGear(gear.lower())
            if gear.lower() in DepthGear._value2member_map_
            else DepthGear.VERBATIM
        )
        chosen_voice = voice or (settings.cantoleaf_tts_voice if tts_name == "edge" else None)

        pipeline = SynthesisPipeline(tts, AudioCache(), UsageTracker())
        utterances = await generate_depth_stream(
            book.book_id, ch, chosen_gear, LangMode.SOURCE, adapt
        )

        console.print(
            f"\n[bold green]Chapter {ch_idx + 1}: {ch.title}[/bold green] ({len(utterances)} utterances)"
        )
        for idx, u in enumerate(utterances[:5]):
            span = await pipeline.synthesize_utterance(u, voice=chosen_voice)
            console.print(
                f"[{idx + 1}] [dim]({span.duration_sec:.1f}s)[/dim] {span.audio_path.name}"
            )
        if len(utterances) > 5:
            console.print(
                f"[dim]... and {len(utterances) - 5} more utterances ready in cache.[/dim]\n"
            )

    asyncio.run(_run())


@app.command()
def studio(
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind"),
    port: int = typer.Option(8000, "--port", help="Port to bind CantoLeaf Studio server"),
) -> None:
    """Launch the interactive CantoLeaf Studio web reader UI."""
    import uvicorn

    console.print(
        f"\n[bold green]Launching CantoLeaf Studio[/bold green] on [cyan]http://{host}:{port}[/cyan]..."
    )
    uvicorn.run("cantoleaf.web.app:app", host=host, port=port, reload=False)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
