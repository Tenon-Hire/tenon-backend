"""Application module for simulations services simulations scenario generation story service workflows."""

from __future__ import annotations

from collections.abc import Callable

from app.simulations.services.simulations_services_simulations_scenario_generation_text_service import (
    normalize_text,
    seed_from_inputs,
)

PickFn = Callable[[tuple[str, ...], int, int], str]
TemplateNameFn = Callable[[str], str]


def build_storyline_markdown(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
    storyline_contexts: tuple[str, ...],
    storyline_constraints: tuple[str, ...],
    pick: PickFn,
    template_display_name: TemplateNameFn,
) -> str:
    """Build storyline markdown."""
    seed = seed_from_inputs(role, tech_stack, template_key)
    display_name = template_display_name(template_key)
    context = pick(storyline_contexts, seed, 1)
    constraint = pick(storyline_constraints, seed, 2)
    role_label = normalize_text(role) or "Software Engineer"
    stack_label = normalize_text(tech_stack) or "general backend stack"
    return "\n".join(
        [
            f"# {role_label} Scenario v1",
            "",
            f"You are joining a product team shipping services on **{stack_label}**.",
            f"The repository baseline uses the **{display_name}** template and the team is currently working on {context}.",
            "Your mandate is to deliver a safe, production-quality increment with "
            f"{constraint} while keeping communication clear for reviewers.",
        ]
    )


def build_task_description(
    *,
    day_index: int,
    role: str,
    tech_stack: str,
    template_key: str,
    code_priorities: tuple[str, ...],
    debug_signals: tuple[str, ...],
    pick: PickFn,
    template_display_name: TemplateNameFn,
) -> str:
    """Build task description."""
    seed = seed_from_inputs(role, tech_stack, template_key)
    priority = pick(code_priorities, seed, 10 + day_index)
    debug_signal = pick(debug_signals, seed, 20 + day_index)
    stack_label = normalize_text(tech_stack) or "the target stack"
    template_name = template_display_name(template_key)
    if day_index == 1:
        return f"Draft an implementation plan that defines service boundaries, key data flows, API contracts, and risk controls. Include concrete tradeoffs and how you will validate correctness in {stack_label}."
    if day_index == 2:
        return f"Implement the primary backend slice in code with tests. Prioritize {priority} and keep the solution aligned with the {template_name} project structure."
    if day_index == 3:
        return f"Investigate and fix a failing behavior path. Treat {debug_signal} as the anchor signal, isolate root cause, and add regression coverage."
    if day_index == 4:
        return "Refactor for maintainability and handoff quality. Leave clear comments, reduce cognitive load, and document operational implications of your changes."
    return "Write a structured engineering reflection covering decisions, tradeoffs, risk handling, and what you would improve with one additional iteration."


__all__ = ["build_storyline_markdown", "build_task_description"]
