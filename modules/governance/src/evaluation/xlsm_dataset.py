from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from defusedxml import ElementTree
from zipfile import ZipFile

from modules.governance.contracts.evaluation import DocumentRecord, PublicEvaluationScenario, UserRecord


_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_REQUIRED_HEADERS = {
    "Document_Metadata": ("document_id", "title", "department", "classification", "allowed_access"),
    "Users": ("user_id", "department", "role", "status"),
    "Public_Evaluation": (
        "question_id",
        "user_id",
        "user_role",
        "user_department",
        "expected_permission",
        "expected_document_id",
    ),
}


@dataclass(frozen=True)
class WorkbookEvaluationDataset:
    documents: MappingProxyType
    users: MappingProxyType
    scenarios: tuple[PublicEvaluationScenario, ...]


def _normalize(value: str) -> str:
    value = " ".join(value.split())
    return "Human Resources" if value == "HR" else value


def _cell_column(reference: str) -> str:
    return "".join(character for character in reference if character.isalpha())


def _shared_strings(archive: ZipFile) -> tuple[str, ...]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return ()
    root = ElementTree.fromstring(archive.read(path))
    return tuple("".join(item.itertext()) for item in root.findall(f"{{{_MAIN}}}si"))


def _sheet_paths(archive: ZipFile) -> dict[str, str]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        relation.attrib["Id"]: relation.attrib["Target"].lstrip("/")
        for relation in relationships.findall(f"{{{_PKG_REL}}}Relationship")
    }
    paths = {}
    for sheet in workbook.findall(f".//{{{_MAIN}}}sheet"):
        target = targets[sheet.attrib[f"{{{_REL}}}id"]]
        paths[sheet.attrib["name"]] = target if target.startswith("xl/") else f"xl/{target}"
    return paths


def _rows(archive: ZipFile, path: str, shared_strings: tuple[str, ...]) -> dict[int, dict[str, str]]:
    root = ElementTree.fromstring(archive.read(path))
    rows = {}
    for row in root.findall(f".//{{{_MAIN}}}sheetData/{{{_MAIN}}}row"):
        values = {}
        for cell in row.findall(f"{{{_MAIN}}}c"):
            cell_type = cell.attrib.get("t")
            value = cell.findtext(f"{{{_MAIN}}}v", default="")
            if cell_type == "s":
                value = shared_strings[int(value)]
            elif cell_type == "inlineStr":
                value = "".join(cell.find(f"{{{_MAIN}}}is").itertext())
            values[_cell_column(cell.attrib["r"])] = value
        rows[int(row.attrib["r"])] = values
    return rows


def _table(archive: ZipFile, path: str, shared_strings: tuple[str, ...], required_headers: tuple[str, ...]):
    rows = _rows(archive, path, shared_strings)
    header_row = next(
        (
            row_number
            for row_number, row in rows.items()
            if set(required_headers).issubset({_normalize(value) for value in row.values()})
        ),
        None,
    )
    if header_row is None:
        raise ValueError("worksheet is missing expected headers")
    headers = {column: _normalize(value) for column, value in rows[header_row].items()}
    records = []
    for row_number, row in rows.items():
        if row_number <= header_row:
            continue
        record = {header: _normalize(row.get(column, "")) for column, header in headers.items()}
        if not any(record.values()):
            continue
        if any(record[header] == "" for header in required_headers):
            raise ValueError("worksheet contains incomplete required data")
        records.append(record)
    return tuple(records)


def _unique(records, key: str):
    result = {}
    for record in records:
        if record[key] in result:
            raise ValueError(f"duplicate {key}: {record[key]}")
        result[record[key]] = record
    return result


def load_public_evaluation_dataset(workbook_path) -> WorkbookEvaluationDataset:
    with ZipFile(Path(workbook_path)) as archive:
        sheets = _sheet_paths(archive)
        if missing := set(_REQUIRED_HEADERS) - set(sheets):
            raise ValueError(f"missing worksheets: {', '.join(sorted(missing))}")
        shared_strings = _shared_strings(archive)
        tables = {
            name: _table(archive, sheets[name], shared_strings, headers)
            for name, headers in _REQUIRED_HEADERS.items()
        }

    document_rows = _unique(tables["Document_Metadata"], "document_id")
    user_rows = _unique(tables["Users"], "user_id")
    documents = {
        document_id: DocumentRecord(
            document_id,
            row["title"],
            row["department"],
            row["classification"],
            row["allowed_access"],
        )
        for document_id, row in document_rows.items()
    }
    users = {
        user_id: UserRecord(user_id, row["role"], row["department"], row["status"])
        for user_id, row in user_rows.items()
    }
    scenarios = []
    for row in _unique(tables["Public_Evaluation"], "question_id").values():
        document_ids = tuple(item.strip() for item in row["expected_document_id"].split(";") if item.strip())
        if row["user_id"] not in users or not document_ids or any(item not in documents for item in document_ids):
            raise ValueError(f"scenario {row['question_id']} has an unknown reference")
        scenarios.append(PublicEvaluationScenario(
            row["question_id"],
            row["user_id"],
            row["user_role"],
            row["user_department"],
            row["expected_permission"],
            document_ids,
        ))
    return WorkbookEvaluationDataset(MappingProxyType(documents), MappingProxyType(users), tuple(scenarios))
