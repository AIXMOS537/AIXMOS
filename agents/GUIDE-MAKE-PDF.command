#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")"
echo ""
echo "  Rendering AIXMOS-GUIDE.md to HTML + PDF..."
echo ""

# Step 1: md -> html
node lib/build-guide.js
if [ $? -ne 0 ]; then
  echo "  md->html failed."
  read -p "  Press Enter to close..."
  exit 1
fi

# Step 2: html -> pdf via Chrome/Edge headless
CHROME=""
for candidate in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"; do
  if [ -x "$candidate" ]; then
    CHROME="$candidate"
    break
  fi
done

if [ -z "$CHROME" ]; then
  echo "  No Chrome/Edge/Chromium/Brave found in /Applications."
  echo "  Opening the HTML in your default browser instead — use File > Print > Save as PDF."
  open AIXMOS-GUIDE.html
  read -p "  Press Enter to close..."
  exit 0
fi

HERE_PATH="$(pwd)/AIXMOS-GUIDE.html"
PDF_PATH="$(pwd)/AIXMOS-GUIDE.pdf"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer "--print-to-pdf=$PDF_PATH" "file://$HERE_PATH" 2>/dev/null

if [ -f "$PDF_PATH" ]; then
  echo "  Done:"
  echo "    AIXMOS-GUIDE.md   (source)"
  echo "    AIXMOS-GUIDE.html (browser view)"
  echo "    AIXMOS-GUIDE.pdf  (print ready)"
  open "$PDF_PATH"
else
  echo "  PDF render failed. Opening HTML in browser instead."
  open AIXMOS-GUIDE.html
fi
echo ""
read -p "  Press Enter to close..."
