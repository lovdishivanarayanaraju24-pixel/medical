#!/usr/bin/env bash

# ==============================================================================
# Script Name: setup_issues.sh
# Description: Populates GitLab issues with defined estimates, labels, and due
#              dates for the Lab Report Structured Extractor project.
#
# Requirements:
#   1. The 'glab' CLI must be installed and authenticated.
#      Run: glab auth login
#   2. Run this script within the local git repository associated with the
#      GitLab project.
# ==============================================================================

set -euo pipefail

# Today's date (Phase 1/2 tasks due today)
TODAY="2026-06-28"

# Assignee placeholders (to be updated by user or matched automatically)
ASSIGNEE_A="[member-a]"
ASSIGNEE_B="[member-b]"
ASSIGNEE_C="[member-c]"

echo "Checking GitLab CLI authentication status..."
if ! glab auth status &>/dev/null; then
    echo "ERROR: glab is not authenticated. Please run 'glab auth login' before executing this script."
    exit 1
fi

echo "Creating issues on GitLab..."

# ------------------------------------------------------------------------------
# 1. OCR Ingestion Pipeline
# ------------------------------------------------------------------------------
glab issue create \
  --title "Implement Core OCR Ingestion Pipeline" \
  --description "Set up local pdf-to-image conversion using pdf2image and OCR text extraction using pytesseract. Must read text blocks locally on CPU with zero network calls." \
  --assignee "$ASSIGNEE_A" \
  --label "estimate::2.5h,phase::2" \
  --due-date "$TODAY"

# ------------------------------------------------------------------------------
# 2. Regex Tabular Parser & Schema Validation
# ------------------------------------------------------------------------------
glab issue create \
  --title "Develop Tabular Regex Parser and Schema Validation" \
  --description "Construct deterministic regular expression rules to parse tabular results (test name, value, unit, reference range, abnormal flag) and validate against JSON Schema." \
  --assignee "$ASSIGNEE_A" \
  --label "estimate::3h,phase::2" \
  --due-date "$TODAY"

# ------------------------------------------------------------------------------
# 3. SQLite Storage Layer
# ------------------------------------------------------------------------------
glab issue create \
  --title "Design SQLite Database Schema and Persistence Layer" \
  --description "Build database schema, setup scripts, and python CRUD module to store report metadata and parsed measurement rows." \
  --assignee "$ASSIGNEE_A" \
  --label "estimate::1.5h,phase::2" \
  --due-date "$TODAY"

# ------------------------------------------------------------------------------
# 4. Streamlit UI Dashboard
# ------------------------------------------------------------------------------
glab issue create \
  --title "Build Streamlit Front-End UI Dashboard" \
  --description "Create Streamlit interface featuring file drag-and-drop, result inspection table, test selection dropdowns, and historical trend plotting charts." \
  --assignee "$ASSIGNEE_B" \
  --label "estimate::3.5h,phase::2" \
  --due-date "$TODAY"

# ------------------------------------------------------------------------------
# 5. Local LLM Note Summarizer
# ------------------------------------------------------------------------------
glab issue create \
  --title "Integrate Local LLM Note Summarizer (llama.cpp)" \
  --description "Integrate llama.cpp wrapper to load a 1.5B/3B GGUF model offline, allowing translation of doctor impressions/notes into plain English." \
  --assignee "$ASSIGNEE_C" \
  --label "estimate::2.5h,phase::3" \
  --due-date "$TODAY"

# ------------------------------------------------------------------------------
# 6. CI/CD Code Quality & Security Pipeline
# ------------------------------------------------------------------------------
glab issue create \
  --title "Configure Multi-Check CI/CD Quality Pipeline" \
  --description "Set up gitlab-ci.yml containing linters, formatters, type-checkers, and security scanners (black, ruff, mypy, bandit, pip-audit, gitleaks, commitlint, license check)." \
  --assignee "$ASSIGNEE_C" \
  --label "estimate::2h,phase::2" \
  --due-date "$TODAY"

# ------------------------------------------------------------------------------
# 7. Offline E2E Validation Script
# ------------------------------------------------------------------------------
glab issue create \
  --title "Create Offline E2E Verification Demo Script" \
  --description "Implement validation pipeline runner script that tests the end-to-end flow offline (Wi-Fi off) with a sample CBC lab report and asserts parsed criteria." \
  --assignee "$ASSIGNEE_C" \
  --label "estimate::1.5h,phase::3" \
  --due-date "$TODAY"

# ------------------------------------------------------------------------------
# 8. Documentation Package (README/CHANGELOG/CONTRIBUTING)
# ------------------------------------------------------------------------------
glab issue create \
  --title "Finalize Project Documentation Package" \
  --description "Refine README guidelines, generate a clean CHANGELOG draft, and set up a CONTRIBUTING instruction file for new team contributors." \
  --assignee "$ASSIGNEE_B" \
  --label "estimate::1h,phase::3" \
  --due-date "$TODAY"

echo "All MVP planning issues successfully queued in script."
echo "Note: Make sure to replace assignee placeholders with your team members' GitLab usernames before running."
