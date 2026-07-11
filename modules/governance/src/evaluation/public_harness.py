from modules.governance.contracts.evaluation import EvaluationResult
from modules.governance.src.evaluation.public_rbac import allows


def evaluate_public_cases(dataset):
    results = []
    for scenario in dataset.scenarios:
        user = dataset.users[scenario.user_id]
        persona = type(user)(user.user_id, scenario.role, scenario.department, user.status)
        allowed_ids = tuple(
            document_id
            for document_id in scenario.expected_document_ids
            if allows(persona, dataset.documents[document_id])
        )
        actual_permission = "Allow" if len(allowed_ids) == len(scenario.expected_document_ids) else "Deny"
        exported_ids = allowed_ids if actual_permission == "Allow" else ()
        results.append(EvaluationResult(
            scenario.question_id,
            scenario.expected_permission,
            actual_permission,
            exported_ids,
            exported_ids,
        ))
    return tuple(results)
