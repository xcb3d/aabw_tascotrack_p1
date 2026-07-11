from modules.governance.contracts.evaluation import DocumentRecord, UserRecord


def allows(user: UserRecord, document: DocumentRecord) -> bool:
    # ponytail: workbook evaluation oracle only; replace with BE policy decisions at runtime.
    if user.status != "Active" or user.role not in {"Employee", "Manager", "Director", "Executive"}:
        return False
    if document.classification in {"Public", "Internal"}:
        return True
    if document.classification == "Confidential":
        return user.role == "Executive" or user.department == document.department
    if document.classification == "Restricted":
        return user.role == "Executive"
    return False
