"""Research report export — Markdown and PDF."""

from __future__ import annotations

from typing import Any


def export_report_markdown(report: dict[str, Any], *, query: str = "") -> str:
    title = report.get("title") or query or "Research Report"
    lines = [f"# {title}", ""]
    if report.get("executive_summary"):
        lines.extend(["## Executive Summary", report["executive_summary"], ""])
    if report.get("key_findings"):
        lines.extend(["## Key Findings", ""])
        lines.extend(f"- {item}" for item in report["key_findings"])
        lines.append("")
    if report.get("detailed_analysis"):
        lines.extend(["## Detailed Analysis", report["detailed_analysis"], ""])
    if report.get("evidence_summary"):
        lines.extend(["## Evidence Summary", report["evidence_summary"], ""])
    if report.get("contradictions_noted"):
        lines.extend(["## Contradictions", ""])
        lines.extend(f"- {item}" for item in report["contradictions_noted"])
        lines.append("")
    score = report.get("confidence_score")
    if score is not None:
        lines.extend([f"**Confidence score:** {score}", ""])
    refs = report.get("references") or report.get("sources_reviewed") or []
    if refs:
        lines.extend(["## References", ""])
        for ref in refs:
            if isinstance(ref, dict):
                label = ref.get("label") or ref.get("url") or "Source"
                url = ref.get("url")
                lines.append(f"- [{label}]({url})" if url else f"- {label}")
            else:
                lines.append(f"- {ref}")
    return "\n".join(lines)


def export_report_pdf_bytes(report: dict[str, Any], *, query: str = "") -> bytes:
    """Minimal PDF (text lines) without external PDF libraries."""
    markdown = export_report_markdown(report, query=query)
    lines = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in markdown.splitlines()]
    content_lines = ["BT", "/F1 11 Tf", "50 750 Td", "14 TL"]
    for index, line in enumerate(lines[:80]):
        prefix = "T*" if index else ""
        if prefix:
            content_lines.append(prefix)
        content_lines.append(f"({line[:90]}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    header = b"%PDF-1.4\n"
    body = b""
    xref_positions = [0]
    offset = len(header)
    for obj in objects:
        xref_positions.append(offset)
        body += obj
        offset += len(obj)
    xref_start = offset
    xref = b"xref\n0 " + str(len(xref_positions)).encode() + b"\n"
    xref += b"0000000000 65535 f \n"
    for pos in xref_positions[1:]:
        xref += f"{pos:010d} 00000 n \n".encode()
    trailer = (
        b"trailer<< /Size "
        + str(len(xref_positions)).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_start).encode()
        + b"\n%%EOF"
    )
    return header + body + xref + trailer
