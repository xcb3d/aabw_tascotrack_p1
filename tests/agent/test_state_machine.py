import unittest

from modules.agent.contracts.run import ExecutionRoute, RunBudget, RunState, RunStatus
from modules.agent.src.orchestration.state_machine import InvalidTransition, transition


class StateMachineTest(unittest.TestCase):
    def test_successful_deterministic_completion_preserves_route(self):
        state = RunState.new()
        state = transition(state, RunStatus.SENSITIVITY_CHECKED)
        state = transition(state, RunStatus.AUTHORIZED)
        state = transition(state, RunStatus.ROUTED, route=ExecutionRoute.DETERMINISTIC)
        state = transition(state, RunStatus.DETERMINISTIC)
        state = transition(state, RunStatus.VALIDATING_OUTPUT)
        state = transition(state, RunStatus.COMPLETED)

        self.assertEqual(state.status, RunStatus.COMPLETED)
        self.assertIs(state.route, ExecutionRoute.DETERMINISTIC)

    def test_sensitivity_denial(self):
        state = RunState.new()
        state = transition(state, RunStatus.SENSITIVITY_CHECKED)
        state = transition(state, RunStatus.DENIED)

        self.assertEqual(state.status, RunStatus.DENIED)
        self.assertIsNone(state.route)

    def test_invalid_jump_from_received_to_completed(self):
        with self.assertRaises(InvalidTransition):
            transition(RunState.new(), RunStatus.COMPLETED)

    def test_rejects_simple_rag_at_routed(self):
        state = transition(RunState.new(), RunStatus.SENSITIVITY_CHECKED)
        state = transition(state, RunStatus.AUTHORIZED)

        with self.assertRaises(InvalidTransition):
            transition(state, RunStatus.ROUTED, route=ExecutionRoute.SIMPLE_RAG)

    def test_deterministic_budget_has_zero_allowances_and_three_second_deadline(self):
        budget = RunBudget.deterministic()

        self.assertEqual(budget.deadline_seconds, 3)
        self.assertEqual(budget.model_calls, 0)
        self.assertEqual(budget.tool_calls, 0)
        self.assertEqual(budget.retrieval_calls, 0)

    def test_budget_restriction_cannot_relax_model_calls_but_can_reduce_deadline(self):
        budget = RunBudget(deadline_seconds=3, model_calls=1, tool_calls=0, retrieval_calls=0)

        with self.assertRaises(ValueError):
            budget.restrict(model_calls=2)

        restricted = budget.restrict(deadline_seconds=2)
        self.assertEqual(restricted.deadline_seconds, 2)
        self.assertEqual(restricted.model_calls, 1)

    def test_budget_restriction_rejects_non_integer_limits(self):
        budget = RunBudget(deadline_seconds=3, model_calls=1, tool_calls=0, retrieval_calls=0)

        for value in (float("nan"), float("inf"), 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    budget.restrict(deadline_seconds=value)


if __name__ == "__main__":
    unittest.main()
