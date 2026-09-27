#!/usr/bin/env bash
set -e

APP_DIR="$HOME/projects/My-Tools/youtube_visual_collector_gui"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/Desktop"
APPLICATIONS_DIR="$HOME/.local/share/applications"

CURRENT_DIR="$(pwd -P)"
SOURCE_SCRIPT="$CURRENT_DIR/youtube_visual_collector.py"
SOURCE_SRC_DIR="$CURRENT_DIR/src"
SOURCE_DOCS_DIR="$CURRENT_DIR/docs"
SOURCE_REQUIREMENTS="$CURRENT_DIR/requirements.txt"

if [ ! -f "$SOURCE_SCRIPT" ]; then
  echo "ERROR: youtube_visual_collector.py not found in current folder."
  echo "Run this installer from the extracted package folder."
  exit 1
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$APPLICATIONS_DIR"

# If installer is running from the same install folder, do not copy file onto itself.
# If running from another folder, update the installed script.
if [ "$(realpath "$SOURCE_SCRIPT")" != "$(realpath "$APP_DIR/youtube_visual_collector.py" 2>/dev/null || echo "$APP_DIR/youtube_visual_collector.py")" ]; then
  cp "$SOURCE_SCRIPT" "$APP_DIR/youtube_visual_collector.py"
else
  echo "Source and destination are the same file. Keeping current script in place."
fi

chmod +x "$APP_DIR/youtube_visual_collector.py"

SOURCE_PACKAGE="$SOURCE_SRC_DIR/creator_video_collector"
TARGET_PACKAGE="$APP_DIR/src/creator_video_collector"
if [ -d "$SOURCE_PACKAGE" ]; then
  mkdir -p "$APP_DIR/src"
  if [ "$(realpath "$SOURCE_PACKAGE")" != "$(realpath "$TARGET_PACKAGE" 2>/dev/null || echo "$TARGET_PACKAGE")" ]; then
    rm -rf "$TARGET_PACKAGE"
    cp -R "$SOURCE_PACKAGE" "$TARGET_PACKAGE"
  else
    echo "Source and destination package are the same folder. Keeping current package in place."
  fi
fi

if [ -d "$SOURCE_DOCS_DIR" ]; then
  mkdir -p "$APP_DIR/docs"
  if [ "$(realpath "$SOURCE_DOCS_DIR")" != "$(realpath "$APP_DIR/docs" 2>/dev/null || echo "$APP_DIR/docs")" ]; then
    cp -R "$SOURCE_DOCS_DIR/." "$APP_DIR/docs/"
  else
    echo "Source and destination docs are the same folder. Keeping current docs in place."
  fi
fi

if [ -f "$SOURCE_REQUIREMENTS" ]; then
  if [ "$(realpath "$SOURCE_REQUIREMENTS")" != "$(realpath "$APP_DIR/requirements.txt" 2>/dev/null || echo "$APP_DIR/requirements.txt")" ]; then
    cp "$SOURCE_REQUIREMENTS" "$APP_DIR/requirements.txt"
  else
    echo "Source and destination requirements are the same file. Keeping current requirements in place."
  fi
fi

cat > "$BIN_DIR/youtube-visual-collector" <<EOF
#!/usr/bin/env bash
python3 "$APP_DIR/youtube_visual_collector.py"
EOF
chmod +x "$BIN_DIR/youtube-visual-collector"

cat > "$APPLICATIONS_DIR/youtube-visual-collector.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Creator Video Collector
Comment=Download videos, covers, subtitles, and clean TXT transcripts
Exec=$BIN_DIR/youtube-visual-collector
Icon=$APP_DIR/assets/creator-video-collector.svg
Terminal=false
Categories=Utility;AudioVideo;
EOF

chmod +x "$APPLICATIONS_DIR/youtube-visual-collector.desktop"

SOURCE_ICON="$CURRENT_DIR/assets/creator-video-collector.svg"
TARGET_ICON="$APP_DIR/assets/creator-video-collector.svg"
if [ -f "$SOURCE_ICON" ]; then
  mkdir -p "$APP_DIR/assets"
  if [ "$(realpath "$SOURCE_ICON")" != "$(realpath "$TARGET_ICON" 2>/dev/null || echo "$TARGET_ICON")" ]; then
    cp "$SOURCE_ICON" "$TARGET_ICON"
  else
    echo "Source and destination icon are the same file. Keeping current icon in place."
  fi
fi

cp "$APPLICATIONS_DIR/youtube-visual-collector.desktop" "$DESKTOP_DIR/Creator Video Collector.desktop"
chmod +x "$DESKTOP_DIR/Creator Video Collector.desktop"
gio set "$DESKTOP_DIR/Creator Video Collector.desktop" metadata::trusted true 2>/dev/null || true

echo ""
echo "Installed / updated successfully with no conflict."
echo ""
echo "Tool path:"
echo "  $APP_DIR"
echo ""
echo "Run from terminal:"
echo "  youtube-visual-collector"
echo ""
echo "Desktop launcher:"
echo "  $DESKTOP_DIR/Creator Video Collector.desktop"
