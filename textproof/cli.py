from __future__ import annotations

import click
from pathlib import Path

from textproof.scanner import scan_directory
from textproof.rules import Rules
from textproof.compare import compare, diff_summary
from textproof.report import generate_report
from textproof.fixer import apply_fixes


@click.group()
@click.version_option("0.1.0", prog_name="textproof")
def main() -> None:
    """textproof — 批量校对命令行工具，检查成组文本一致性"""


@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("-p", "--pattern", default="*.md", help="文件名匹配模式（默认 *.md）")
@click.option(
    "-i",
    "--ignore",
    "ignore_files",
    multiple=True,
    help="要忽略的文件（可重复指定）",
)
def scan(directory: str, pattern: str, ignore_files: tuple[str, ...]) -> None:
    """扫描目录，列出匹配文件并按分组归集"""
    result = scan_directory(directory, pattern=pattern, ignore_files=list(ignore_files))
    click.echo(f"扫描目录：{directory}")
    click.echo(f"匹配文件：{len(result.files)} 个")
    click.echo()
    for f in result.files:
        click.echo(f"  {f}")
    click.echo()
    click.echo("分组：")
    for group, files in sorted(result.groups.items()):
        click.echo(f"  {group} ({len(files)} 个文件)")
        for f in files:
            click.echo(f"    - {f}")


@main.command("compare")
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("-r", "--rules", "rules_file", type=click.Path(exists=True), help="规则文件路径（JSON/YAML）")
@click.option("-p", "--pattern", default="*.md", help="文件名匹配模式")
@click.option(
    "-i",
    "--ignore",
    "ignore_files",
    multiple=True,
    help="要忽略的文件",
)
def compare_cmd(directory: str, rules_file: str | None, pattern: str, ignore_files: tuple[str, ...]) -> None:
    """比对成组文件，输出差异摘要，按严重程度分组"""
    rules = Rules()
    if rules_file:
        rules = Rules.from_file(rules_file)
    result = compare(directory, rules, pattern=pattern, ignore_files=list(ignore_files))
    click.echo(diff_summary(result))


@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("-r", "--rules", "rules_file", type=click.Path(exists=True), help="规则文件路径")
@click.option("-p", "--pattern", default="*.md", help="文件名匹配模式")
@click.option(
    "-i",
    "--ignore",
    "ignore_files",
    multiple=True,
    help="要忽略的文件",
)
@click.option("-o", "--output", type=click.Path(), help="报告输出文件路径")
@click.option("-f", "--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="报告格式")
def report(
    directory: str,
    rules_file: str | None,
    pattern: str,
    ignore_files: tuple[str, ...],
    output: str | None,
    fmt: str,
) -> None:
    """生成简明校对报告"""
    rules = Rules()
    if rules_file:
        rules = Rules.from_file(rules_file)
    result = compare(directory, rules, pattern=pattern, ignore_files=list(ignore_files))
    text = generate_report(result, output=output, fmt=fmt)
    if not output:
        click.echo(text)
    else:
        click.echo(f"报告已写入：{output}")


@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("-r", "--rules", "rules_file", type=click.Path(exists=True), help="规则文件路径")
@click.option("-p", "--pattern", default="*.md", help="文件名匹配模式")
@click.option(
    "-i",
    "--ignore",
    "ignore_files",
    multiple=True,
    help="要忽略的文件",
)
@click.option("--yes", is_flag=True, help="跳过交互确认，直接应用所有修正")
def fix(
    directory: str,
    rules_file: str | None,
    pattern: str,
    ignore_files: tuple[str, ...],
    yes: bool,
) -> None:
    """交互式确认并自动修正常见不一致"""
    rules = Rules()
    if rules_file:
        rules = Rules.from_file(rules_file)
    result = compare(directory, rules, pattern=pattern, ignore_files=list(ignore_files))

    click.echo(diff_summary(result))
    click.echo()

    fixable = [i for i in result.issues if i.suggestion and i.original]
    if not fixable:
        click.echo("没有可自动修正的问题。")
        return

    click.echo(f"可修正问题：{len(fixable)} 个")
    applied = apply_fixes(directory, fixable, interactive=not yes)
    click.echo(f"已应用修正：{applied} 处")


if __name__ == "__main__":
    main()
