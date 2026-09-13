"""Pinned golangci-lint identity for the Phase 6A baseline."""

from __future__ import annotations

GOLANGCI_VERSION = "2.13.2"
GOLANGCI_RELEASE_TAG = "v2.13.2"
TOOL_NAME = "golangci-lint"

# Official release checksums for v2.13.2
# (https://github.com/golangci/golangci-lint/releases/download/v2.13.2/golangci-lint-2.13.2-checksums.txt).
RELEASE_SHA256 = {
    "golangci-lint-2.13.2-windows-amd64.zip": (
        "4735fdc8e84a0cfb7a15a1c364a650942f88215e0d36c674ebc4024f7b554524"
    ),
    "golangci-lint-2.13.2-linux-amd64.tar.gz": (
        "2277d43b98ec0054280f2ac26b53268bae97682444678a59a657dd565da021d6"
    ),
    "golangci-lint-2.13.2-darwin-amd64.tar.gz": (
        "8a13aaf9cbbb1dee52824e862cf0d0720e5bb97c1f4260d1e51623a09492b57b"
    ),
    "golangci-lint-2.13.2-darwin-arm64.tar.gz": (
        "f4bf83f0b64f055c42b28fc9a38861839f69c096e61c788e72dfaae412011789"
    ),
}

RELEASE_ASSET = {
    ("windows", "amd64"): "golangci-lint-2.13.2-windows-amd64.zip",
    ("linux", "amd64"): "golangci-lint-2.13.2-linux-amd64.tar.gz",
    ("darwin", "amd64"): "golangci-lint-2.13.2-darwin-amd64.tar.gz",
    ("darwin", "arm64"): "golangci-lint-2.13.2-darwin-arm64.tar.gz",
}

DEFAULT_BUILD_TAGS = ("sqlite_fts5",)

FINDING_FIELDS = (
    "pr_number",
    "tool",
    "tool_version",
    "commit_sha",
    "file",
    "line",
    "column",
    "rule",
    "message",
    "severity",
    "raw_finding_id",
)

MANIFEST_FIELDS = (
    "pr_number",
    "commit_sha",
    "tool_version",
    "config_hash",
    "exit_code",
    "finding_count",
    "execution_status",
    "diff_mode",
    "first_parent_empty",
    "build_tags",
    "raw_issue_count",
    "dropped_outside_diff",
    "analyzed_go_file_count",
)
