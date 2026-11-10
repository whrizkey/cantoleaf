import shutil
import sys

import typer
from rich.console import Console
from rich.table import Table

from cantoleaf import __version__
from cantoleaf.config import get_settings

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
    table.add_column("Component", style="dim", width=22)
    table.add_column("Status", width=12)
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

    settings = get_settings()

    # TTS provider status
    table.add_row(
        "Default TTS Provider",
        "[cyan]CONFIGURED[/cyan]",
        f"{settings.cantoleaf_tts_provider} (voice: {settings.cantoleaf_tts_voice})",
    )

    # Adapt provider status
    table.add_row(
        "Default Adapt Provider",
        "[cyan]CONFIGURED[/cyan]",
        f"{settings.cantoleaf_adapt_provider} (model: {settings.cantoleaf_adapt_model or 'default'})",
    )

    # Budget cap
    table.add_row(
        "Spend Protection Cap",
        "[green]ACTIVE[/green]",
        f"${settings.cantoleaf_max_cost_usd:.2f} max USD per book",
    )

    console.print(table)
    console.print("")


@app.command()
def estimate(
    file_path: str = typer.Argument(..., help="Path to eBook (.epub), PDF, or Markdown file"),
) -> None:
    """Inspect a document's chapters, block classification, and estimated duration per Depth Gear."""
    from cantoleaf.ingest.registry import load_document

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

    # Assumed speaking rate: ~15 characters per second (900 chars/min)
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
