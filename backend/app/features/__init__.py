"""Registry: orchestrator tra cứu module của từng feature ở đây. Đổi implementation = sửa file của role đó, không sửa registry."""
from app.features import f1_scam, f2_detect, f2_redact, f3_filescan
from app.features.base import Analyzer, Redactor
from app.schemas import Feature

ANALYZERS: dict[Feature, Analyzer] = {
    Feature.SCAM: f1_scam.analyze,
    Feature.SENSITIVE: f2_detect.analyze,
    Feature.FILE_SCAN: f3_filescan.analyze,
}
REDACTOR: Redactor = f2_redact.redact
