"""Console script for autosbatch."""

import typer


def main():
    """Main entrypoint."""
    typer.echo("autosbatch  fdsafasfasfq")
    typer.echo("=" * len("autosbatch"))
    typer.echo("submit hundreds of jobs to slurm automatically")


if __name__ == "__main__":
    typer.run(main)
