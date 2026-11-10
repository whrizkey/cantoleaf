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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
