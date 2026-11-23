"""Present the local SMPC protocols as a three-phase terminal walkthrough."""

import re
import subprocess
import sys

from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.models import Parameters
from src.simulation import run_additive, run_shamir


console = Console()
VALUES = [20, 25, 30]


def math_line(markup: str, indent: int = 8) -> None:
    """Print a highlighted calculation with a consistent left margin."""
    console.print(Padding(Text.from_markup(markup), (0, 0, 0, indent)))


def symbol_note(explanation: str) -> None:
    """Show a compact, subdued symbol explanation with a little separation."""
    console.print(Text("│ " + explanation, style="dim italic"))
    console.print()


def show_sharing(trace: dict, parameters: Parameters, shamir: bool) -> None:
    """Explain how each hospital generated the traced shares."""
    title = "Phase 1 - Sharing"
    if shamir:
        title = "Phase 1 - Polynomial sharing"
    console.print(Panel(
        f"Number of hospitals (n): {parameters.n}\n"
        f"Number of servers (m): {parameters.m}\n"
        f"Maximum patients per hospital (M): {parameters.max_value}\n"
        f"Modulus (p): {parameters.p}\n"
        f"Session ID (sid): {trace['session_id']}", title=title
    ))
    symbol_note("Session ID generated using secrets.token_hex(8) to identify this execution.")
    if shamir:
        console.print("Each hospital makes three polynomial shares; server 2 is offline.")
        math_line("[cyan]fᵢ(t) = (xᵢ + aᵢ × t) mod p (degree ≤ 1)[/cyan]", 4)
        symbol_note(
            "i is the hospital; xᵢ is its input, aᵢ its random coefficient, "
            "t the server position, and p the modulus."
        )
        console.print("Now evaluate each hospital's polynomial at the three server positions.")
    else:
        console.print(
            "Each hospital generates three shares because there are three servers, "
            "sending one share to each. The first two are generated randomly, "
            "while the third is calculated to preserve the original value."
        )
        console.print("The random shares are drawn securely from Zₚ (0 to p−1).")
        math_line("[cyan]sᵢ,₃ = (xᵢ − sᵢ,₁ − sᵢ,₂) mod p[/cyan]", 4)
        math_line("[cyan](sᵢ,₁ + sᵢ,₂ + sᵢ,₃) mod p = xᵢ[/cyan]", 4)
        symbol_note(
            "i is the hospital, j the server receiving sᵢ,ⱼ, "
            "xᵢ the input, and p the modulus."
        )
        console.print("Using these values, each hospital calculates its final share as follows:")
    table = Table("Hospital", "Input", "Server 1", "Server 2", "Server 3")
    for hospital_id, value in enumerate(VALUES, start=1):
        shares = []
        for share in trace["generated_shares"]:
            if share.origin == hospital_id:
                shares.append(share.value)
        columns = []
        for server_id, share_value in enumerate(shares, start=1):
            label = str(share_value)
            if shamir and trace["offline_server"] == server_id:
                label += " (not delivered)"
            columns.append(label)
        table.add_row(f"H{hospital_id}", str(value), *columns)
        if shamir:
            coefficient = trace["coefficients"][hospital_id]
            math_line(f"[bold]H{hospital_id} = {value}: a_{hospital_id} = {coefficient}[/bold]", 4)
            math_line(
                f"[cyan]f_{hospital_id}(t) = ({value} + {coefficient} × t) "
                f"mod {parameters.p}[/cyan]"
            )
            for server_id, share_value in enumerate(shares, start=1):
                before_mod = value + coefficient * server_id
                math_line(
                    f"[cyan]t={server_id}: ({value} + {coefficient} × {server_id}) "
                    f"mod {parameters.p}[/cyan]"
                )
                math_line(f"[cyan]= {before_mod} mod {parameters.p}[/cyan]")
                math_line(f"[cyan]= {share_value}[/cyan]")
        else:
            difference = value - shares[0] - shares[1]
            math_line(f"[bold]H{hospital_id} = {value}:[/bold]", 4)
            math_line(
                f"[cyan]s_{hospital_id},3 = "
                f"({value} − {shares[0]} − {shares[1]}) mod {parameters.p}[/cyan]"
            )
            math_line(f"[cyan]= {difference} mod {parameters.p}[/cyan]")
            math_line(f"[cyan]= {shares[2]}[/cyan]")
            math_line(
                f"[bold green]Check: ({shares[0]} + {shares[1]} + {shares[2]}) "
                f"mod {parameters.p}[/bold green]"
            )
            math_line(f"[bold green]= {sum(shares)} mod {parameters.p}[/bold green]")
            math_line(f"[bold green]= {value} ✓[/bold green]")
    if shamir:
        console.print(
            "Shares are generated for each server; only available servers receive theirs:"
        )
    else:
        console.print(
            "The generated shares are distributed as follows, with one share sent to each server:"
        )
    console.print(table)


def show_aggregation(trace: dict, parameters: Parameters) -> None:
    """Explain each available server's traced modular sum."""
    console.print(Panel("Server aggregation", title="Phase 2 - Aggregation"))
    console.print("Each available server adds one share from every hospital.")
    math_line("[cyan]zⱼ = (Σᵢ₌₁ⁿ sᵢ,ⱼ) mod p[/cyan]", 4)
    math_line("[cyan]For n=3: zⱼ = (s₁,ⱼ + s₂,ⱼ + s₃,ⱼ) mod p[/cyan]", 4)
    symbol_note("i is the hospital, j the server receiving shares, zⱼ its partial sum, and p the modulus.")
    console.print("Using the received shares, each server calculates its partial sum as follows:")
    for server_id in range(1, parameters.m + 1):
        if server_id == trace["offline_server"]:
            math_line(f"[bold]Server {server_id} unavailable: no shares delivered or partial sum.[/bold]", 4)
            continue
        received = []
        for share in trace["generated_shares"]:
            if share.destination == server_id:
                received.append(share.value)
        for partial in trace["partial_sums"]:
            if partial.server_id == server_id:
                math_line(
                    f"[bold]Server {server_id} — Received: H1={received[0]}, H2={received[1]}, "
                    f"H3={received[2]}.[/bold]", 4
                )
                math_line(
                    f"[cyan]z_{server_id} = "
                    f"({received[0]} + {received[1]} + {received[2]}) "
                    f"mod {parameters.p}[/cyan]"
                )
                math_line(f"[cyan]= {sum(received)} mod {parameters.p}[/cyan]")
                math_line(f"[cyan]= {partial.value}[/cyan]")


def show_reconstruction(trace: dict, parameters: Parameters, shamir: bool) -> None:
    """Explain the reconstruction using actual server partials."""
    title = "Phase 3 - Reconstruction"
    if shamir:
        title = "Phase 3 - Lagrange Reconstruction"
    console.print(Panel("Analyst reconstruction", title=title))
    if shamir:
        z_1 = 0
        z_3 = 0
        for partial in trace["partial_sums"]:
            if partial.server_id == 1:
                z_1 = partial.value
            if partial.server_id == 3:
                z_3 = partial.value
        inverse = trace["first_denominator_inverse"]
        numerator = 3 * z_1 - z_3
        console.print("Interpolate the total from two server partial sums.")
        math_line("[cyan]S = (v / (v − u) × zᵤ + u / (u − v) × zᵥ) mod p[/cyan]", 4)
        symbol_note(
            "u and v are server positions; zᵤ and zᵥ their partial sums, "
            "p the modulus, and S the total. Division means modular inverse."
        )
        console.print("Now substitute servers 1 and 3 and their actual partial sums.")
        math_line("[bold]With u=1, v=3:[/bold]", 4)
        math_line("[cyan]S = (3 / (3 − 1) × z₁ + 1 / (1 − 3) × z₃) mod p[/cyan]")
        math_line("[cyan]= ((3 × z₁ − z₃) / 2) mod p[/cyan]")
        math_line(f"[cyan]z₁ = {z_1}; z₃ = {z_3}[/cyan]")
        math_line(f"[cyan]pow(2, -1, {parameters.p}) = {inverse}[/cyan]")
        math_line(
            f"[cyan]= ((3 × {z_1} − {z_3}) × {inverse}) mod {parameters.p}[/cyan]"
        )
        math_line(f"[cyan]= ({numerator} × {inverse}) mod {parameters.p}[/cyan]")
        math_line(f"[cyan]= {numerator * inverse} mod {parameters.p}[/cyan]")
        math_line(f"[cyan]= {trace['total']}[/cyan]")
    else:
        values = []
        for partial in trace["partial_sums"]:
            values.append(partial.value)
        console.print("The analyst combines all three server partial sums.")
        math_line("[cyan]S = (Σⱼ₌₁ᵐ zⱼ) mod p[/cyan]", 4)
        math_line("[cyan]For m=3: S = (z₁ + z₂ + z₃) mod p[/cyan]", 4)
        symbol_note("j is the server, zⱼ its partial sum, p the modulus, and S the total.")
        console.print("With the three partial sums received, the analyst reconstructs the total as follows:")
        math_line(f"[bold]Analyst received z₁={values[0]}, z₂={values[1]}, z₃={values[2]}.[/bold]", 4)
        math_line(
            f"[cyan]S = ({values[0]} + {values[1]} + {values[2]}) "
            f"mod {parameters.p}[/cyan]"
        )
        math_line(f"[cyan]= {sum(values)} mod {parameters.p}[/cyan]")
        math_line(f"[cyan]= {trace['total']}[/cyan]")
    math_line(
        f"[bold green]Check: {VALUES[0]} + {VALUES[1]} + {VALUES[2]} "
        f"= {sum(VALUES)} ✓[/bold green]"
    )
    console.print(Panel(
        f"Final Result: S = {trace['total']} patients",
        border_style="green", expand=False,
    ))


def demonstrate(shamir: bool) -> None:
    """Run one protocol and pause between its three presentation phases."""
    parameters = Parameters(n=3, m=3, p=127, max_value=40)
    trace = {}
    if shamir:
        run_shamir(VALUES, parameters, offline_server=2, trace=trace)
    else:
        run_additive(VALUES, parameters, trace=trace)
    show_sharing(trace, parameters, shamir)
    input("Press Enter to continue...")
    show_aggregation(trace, parameters)
    input("Press Enter to continue...")
    show_reconstruction(trace, parameters, shamir)
    input("Press Enter to return to the menu...")


def run_tests() -> None:
    """Describe the test plan and report the existing pytest run faithfully."""
    console.print(
        "These automated tests verify protocol correctness, input validation, "
        "message handling, and server failures."
    )
    console.print(
        "T1–T10 are plan IDs, not a count of pytest functions; additional contract "
        "checks also run. T9 is informative and does not fail solely due to random variation."
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--no-header", "--tb=short", "tests/"],
        check=False, capture_output=True, text=True,
    )
    console.print(result.stdout, markup=False, highlight=False, end="")
    console.print(result.stderr, markup=False, highlight=False, end="")
    summary = ""
    for line in reversed(result.stdout.splitlines()):
        if re.search(r"\b\d+ (?:passed|failed|errors?)\b.*\bin\b", line):
            summary = line
            break
    if summary:
        counts = {"passed": 0, "failed": 0, "error": 0}
        for count, outcome in re.findall(r"\b(\d+) (passed|failed|errors?)\b", summary):
            counts["error" if outcome == "errors" else outcome] = int(count)
        color = "green"
        if result.returncode != 0:
            color = "red"
        console.print(
            f"[bold {color}]Passed: {counts['passed']}; "
            f"failed: {counts['failed']}; errors: {counts['error']}.[/bold {color}]"
        )
    else:
        console.print("Passed/failed/error counts not reported by pytest.")
    status = "passed" if result.returncode == 0 else "failed"
    color = "green"
    if result.returncode != 0:
        color = "red"
    console.print(f"[bold {color}]Tests {status} (exit code {result.returncode}).[/bold {color}]")
    input("Press Enter to return to the menu...")


def main() -> None:
    """Show the four choices until the user exits."""
    while True:
        console.print(
            "\nSMPC Prototype\n\n"
            "1. Additive Secret Sharing (3-of-3)\n"
            "2. Shamir Secret Sharing (2-of-3)\n"
            "3. Run Automated Tests\n"
            "4. Exit\n"
        )
        choice = input("Select an option: ")
        if choice == "4":
            console.print("Goodbye.")
            return
        if choice == "1":
            demonstrate(False)
        elif choice == "2":
            demonstrate(True)
        elif choice == "3":
            run_tests()
        else:
            console.print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
