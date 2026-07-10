"""Cognition package representing the reasoning, prompt building, evaluation, reflection, and self-correction modules."""

from cognition.prompts.prompt_builder import PromptBuilder, prompt_builder
from cognition.parser.response_parser import ResponseParser, response_parser
from cognition.evaluation.output_evaluator import OutputEvaluator, output_evaluator
from cognition.self_correction.error_corrector import ErrorCorrector, error_corrector
from cognition.reflection.self_reflection import SelfReflection, self_reflection
from cognition.reasoning.cognition import CognitionEngine

__all__ = [
    "PromptBuilder",
    "prompt_builder",
    "ResponseParser",
    "response_parser",
    "OutputEvaluator",
    "output_evaluator",
    "ErrorCorrector",
    "error_corrector",
    "SelfReflection",
    "self_reflection",
    "CognitionEngine",
]
