#!/usr/bin/env bash
# UniSat — Generate PDF documentation from Markdown
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"
OUTPUT_DIR="$DOCS_DIR/pdf"

echo "=========================================="
echo "  UniSat Documentation Generator"
echo "=========================================="

# Check dependencies
if ! command -v pandoc &> /dev/null; then
    echo "ERROR: pandoc is required. Install with: sudo apt-get install pandoc"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Generating PDFs..."
for md_file in "$DOCS_DIR"/*.md; do
    basename=$(basename "$md_file" .md)
    echo "  Converting: $basename.md -> $basename.pdf"
    pandoc "$md_file" \
        -o "$OUTPUT_DIR/${basename}.pdf" \
        --pdf-engine=xelatex \
        -V geometry:margin=2.5cm \
        -V fontsize=11pt \
        --highlight-style=tango \
        --toc \
        -V title="UniSat — ${basename}" \
        -V date="$(date '+%Y-%m-%d')" \
        2>/dev/null || echo "    WARNING: Failed to convert $basename (xelatex may not be installed)"
done

echo ""
echo "PDFs generated in: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/*.pdf 2>/dev/null || echo "No PDFs found (pandoc/xelatex may not be installed)"
