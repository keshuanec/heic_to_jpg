# HEIC → JPG / PNG Converter

Offline desktopová aplikace pro macOS pro převod HEIC/HEIF fotek do JPG nebo PNG. Bez omezení počtu souborů.

![Python](https://img.shields.io/badge/Python-3.12+-blue) ![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey)

## Funkce

- Drag & drop souborů nebo složek přímo do okna aplikace
- Dávkový převod bez omezení počtu souborů
- Výstupní formát JPG (nastavitelná kvalita 50–100) nebo PNG
- Výstup vedle originálu nebo do vlastní složky
- Progress bar — GUI nezamrzne ani při stovkách souborů
- Spustitelná ikona v Docku

## Instalace

```bash
git clone https://github.com/keshuanec/heic_to_jpg.git
cd heic_to_jpg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Spuštění

```bash
python3 converter.py
```

## Ikona v Docku (macOS)

1. Vytvoř `.app` bundle na ploše:

```bash
mkdir -p ~/Desktop/"HEIC to JPG.app"/Contents/MacOS
mkdir -p ~/Desktop/"HEIC to JPG.app"/Contents/Resources

cat > ~/Desktop/"HEIC to JPG.app"/Contents/MacOS/"HEIC to JPG" << 'EOF'
#!/bin/bash
exec arch -arm64 \
  "$(pwd)/.venv/bin/python3" \
  "$(pwd)/converter.py"
EOF
chmod +x ~/Desktop/"HEIC to JPG.app"/Contents/MacOS/"HEIC to JPG"

cat > ~/Desktop/"HEIC to JPG.app"/Contents/Info.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>HEIC to JPG</string>
  <key>CFBundleExecutable</key><string>HEIC to JPG</string>
  <key>CFBundleIdentifier</key><string>com.local.heic-to-jpg</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF
```

2. Poklepej na ikonu na ploše → klikni **Otevřít**
3. V Docku klikni pravým tlačítkem na ikonu → **Možnosti → Ponechat v Docku**

## Závislosti

| Balíček | Účel |
|---|---|
| [Pillow](https://python-pillow.org/) | Zpracování a ukládání obrázků |
| [pillow-heif](https://github.com/bigcat88/pillow_heif) | Podpora formátu HEIC/HEIF |
| [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | Drag & drop podpora |
