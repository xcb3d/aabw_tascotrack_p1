from apps.api.src.main import app


def test_all_documented_operation_ids_are_registered() -> None:
    schema = app.openapi()
    documented = {operation["operationId"] for path in schema["paths"].values() for method, operation in path.items() if method in {"get", "post", "put", "patch", "delete"} and "operationId" in operation}
    expected = {
        "getHealth", "listDemoUsers", "listDocuments", "createDocument", "searchKnowledge",
        "legacyChat", "createChatSession", "createAgentRun", "getAgentRun", "streamAgentRunEvents",
        "cancelAgentRun", "getActionPreview", "confirmAction", "rejectAction", "createDocumentVersion",
        "publishDocument", "archiveDocument", "explainPermission", "getRecentAudit", "getTrace",
        "listSecurityEvents", "runPublicEvaluation", "createEvaluationRun", "rebuildIndex",
    }
    assert expected.issubset(documented)
