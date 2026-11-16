"""S5-US26-T01 (#152): versioned SOC investigation prompt templates."""

import re

import pytest

from agent.prompts import load_prompts, output_shape, prompt_version, system_instruction

TASKS = ["review", "initial_assessment", "hypotheses", "evidence", "suggested_actions"]


def test_prompt_set_is_versioned():
    assert re.fullmatch(r"\d+\.\d+\.\d+", prompt_version())
    assert prompt_version() == "1.1.0"
    assert load_prompts()["skill"] == "soc-case-investigator"


@pytest.mark.parametrize("task", TASKS)
def test_every_task_has_an_instruction(task):
    assert len(system_instruction(task)) > 50


@pytest.mark.parametrize("task", TASKS[1:])
def test_output_tasks_declare_their_shape(task):
    assert output_shape(task)


def test_review_declares_the_initial_assessment_shape():
    assert output_shape("review")["initial_assessment"] == {
        "assessment": "string", "cited_alert_ids": ["string"], "gaps": ["string"]
    }


@pytest.mark.parametrize("task", ["system", *TASKS])
def test_untrusted_data_and_citation_rules_are_kept(task):
    prompts = load_prompts()
    tasks = prompts["tasks"]
    text = prompts["system"] if task == "system" else tasks[task]["instruction"]
    if task in ("system", "review"):
        assert "no confiable" in text and "IDs de alertas" in text
    else:
        assert "alert" in text.lower()


def test_unknown_task_fails_loudly():
    with pytest.raises(KeyError):
        system_instruction("nope")
