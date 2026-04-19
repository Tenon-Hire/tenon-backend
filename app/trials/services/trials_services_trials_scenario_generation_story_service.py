"""Application module for trials services trials scenario generation story service workflows."""

from __future__ import annotations

from collections.abc import Callable

from app.trials.services.trials_services_trials_scenario_generation_text_service import (
    normalize_text,
    seed_from_inputs,
)

PickFn = Callable[[tuple[str, ...], int, int], str]


def build_storyline_markdown(
    *,
    role: str,
    tech_stack: str,
    template_key: str,
    storyline_contexts: tuple[str, ...],
    storyline_constraints: tuple[str, ...],
    pick: PickFn,
) -> str:
    """Build storyline markdown."""
    seed = seed_from_inputs(role, tech_stack, template_key)
    context = pick(storyline_contexts, seed, 1)
    constraint = pick(storyline_constraints, seed, 2)
    role_label = normalize_text(role) or "Software Engineer"
    return "\n".join(
        [
            f"# {role_label} Scenario v1",
            "",
            "You are joining a product team with an empty repository and a blank slate.",
            f"The team needs a from-scratch build for {context}.",
            (
                "The trial is intended to surface product judgment, build quality, "
                f"and communication under a two-day implementation window with {constraint}."
            ),
            "Treat the scenario as production hiring work, not an interview toy.",
            (
                "The product area is framed around a realistic company need, and the candidate "
                "is free to choose a reasonable implementation approach."
            ),
        ]
    )


def build_project_brief_markdown(
    *,
    role: str,
    company_context: dict[str, object] | None = None,
    focus: str | None = None,
    preferred_language_framework: str | None = None,
) -> str:
    """Build project brief markdown."""
    role_label = normalize_text(role) or "Software Engineer"
    subject = normalize_text(focus) or "the requested product area"
    preferred_stack = normalize_text(preferred_language_framework)
    domain = None
    product_area = None
    if isinstance(company_context, dict):
        domain = normalize_text(
            company_context.get("domain") or company_context.get("businessDomain")
        )
        product_area = normalize_text(
            company_context.get("productArea") or company_context.get("product_area")
        )
        if not preferred_stack:
            preferred_stack = normalize_text(
                company_context.get("preferredLanguageFramework")
                or company_context.get("preferred_language_framework")
            )
    business_context = "; ".join(
        part
        for part in (
            f"Domain: {domain}" if domain else None,
            f"Product area: {product_area}" if product_area else None,
        )
        if part
    )
    context_lines = [
        "# Project Brief",
        "",
        "## Business Context",
        "",
        f"The team needs a candidate-built system in an empty repo for a {role_label.lower()} engagement.",
        (
            f"The product focus is {subject}. The scenario should feel realistic, scoped, and "
            "open enough to support different valid architectures."
        ),
    ]
    if business_context:
        context_lines.extend([business_context, ""])
    if preferred_stack:
        context_lines.extend(
            [
                "",
                "## Talent Partner Context",
                "",
            ]
        )
        if preferred_stack:
            context_lines.extend(
                [
                    (
                        f"Preferred language/framework: {preferred_stack}. Treat this as context "
                        "only, not as a requirement."
                    )
                ]
            )
    context_lines.extend(
        [
            "",
            "## System Requirements",
            "",
            "- Build the system from scratch in the empty workspace.",
            "- Keep the scope small enough for two implementation days while still feeling production-grade.",
            "- Support one or two core user journeys that require real product and engineering tradeoffs.",
            "- Include enough detail for a strong design doc, implementation plan, demo, and reflection.",
            "",
            "## Technical Constraints",
            "",
            "- Do not prescribe a specific framework, language, or database.",
            "- Keep the architecture open-ended so multiple reasonable stack choices are possible.",
            "- Assume the repo starts with workspace configuration, evidence capture, and this README only.",
            "- Do not require cloned starter code or pre-populated implementation files.",
            "",
            "## Deliverables",
            "",
            "- A working implementation of the requested system.",
            "- Tests that verify the main user flows and a meaningful regression path.",
            "- A concise demo narrative that explains decisions, tradeoffs, and remaining risks.",
            "- A reflection that summarizes what was built and what would come next.",
        ]
    )
    return "\n".join(context_lines).strip()


def build_task_description(
    *,
    day_index: int,
    role: str,
    tech_stack: str,
    template_key: str,
    code_priorities: tuple[str, ...],
    implementation_wrap_up_signals: tuple[str, ...],
    pick: PickFn,
) -> str:
    """Build task description."""
    seed = seed_from_inputs(role, tech_stack, template_key)
    priority = pick(code_priorities, seed, 10 + day_index)
    wrap_up_signal = pick(implementation_wrap_up_signals, seed, 20 + day_index)
    if day_index == 1:
        return "Draft an implementation plan that defines service boundaries, key data flows, API contracts, and risk controls. Include concrete tradeoffs and how you will validate correctness with tests and reviewable artifacts."
    if day_index == 2:
        return f"Implement the primary backend slice in code with tests. Prioritize {priority} and keep the solution aligned with the brief."
    if day_index == 3:
        return (
            "Continue the implementation wrap-up in the same repository used on Day 2. "
            f"Focus on {wrap_up_signal} while finishing implementation details, "
            "tightening tests, improving docs, and polishing the codebase for handoff."
        )
    if day_index == 4:
        return "Prepare a concise demo presentation that walks through the implemented solution, key decisions, tradeoffs, outcomes, and remaining risks for reviewers."
    return "Write a markdown reflection essay covering your experience, challenges, decisions, tradeoffs, communication, and what you would do next."


__all__ = [
    "build_project_brief_markdown",
    "build_storyline_markdown",
    "build_task_description",
]
