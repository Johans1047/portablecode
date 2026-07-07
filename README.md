# portablecode

CLI en Python para migrar configuracion de OpenCode entre PCs.

## Instalacion

```bash
pip install -e .
```

## Cheatsheet de uso

### Exportar

```bash
portablecode export [OPTIONS]
```

| Flag | Descripción |
|------|-------------|
| `-o, --output` | Ruta del archivo de salida (default: `portablecode.portablecode`) |
| `--include-auth` | Incluir credenciales sensibles (`auth.json`) |
| `--include-db` | Incluir base de datos `opencode.db` |
| `--include-binaries` | Incluir binarios Tier 3 (solo funciona en mismo OS) |
| `--include-engram` | Incluir memoria de engram/gentle-ai (transforma paths automáticamente) |

```bash
# Export basico
portablecode export

# Export con nombre custom
portablecode export -o backup-julio.portablecode

# Export completo
portablecode export -o full-backup.portablecode --include-auth --include-db --include-binaries --include-engram
```

### Importar

```bash
portablecode import <archive> [OPTIONS]
```

| Flag | Descripción |
|------|-------------|
| `-f, --force` | Sobreescribir archivos existentes |
| `--skip-auth` | No importar credenciales sensibles (`auth.json`) |

```bash
# Import basico
portablecode import backup.portablecode

# Import forzando sobreescribir
portablecode import backup.portablecode --force

# Import sin credenciales
portablecode import backup.portablecode --skip-auth
```

### Listar archivos

```bash
portablecode list [OPTIONS]
```

| Flag | Descripción |
|------|-------------|
| `-a, --archive` | Listar archivos dentro de un archive |

```bash
# Listar archivos de la config actual
portablecode list

# Listar archivos dentro de un archive
portablecode list -a backup.portablecode
```

### Comparar configs

```bash
# Diferencias entre config actual y un archive
portablecode diff backup.portablecode
```

### Version y ayuda

```bash
portablecode --version
portablecode --help
portablecode export --help
portablecode import --help
```

## Flujo tipico (PC nueva)

```bash
# 1. En la PC vieja: exportar
portablecode export -o mi-config.portablecode

# 2. Copiar mi-config.portablecode a la PC nueva (USB, red, etc.)

# 3. En la PC nueva: instalar OpenCode y gentle-ai/engram
#    (si usas engram, instalalo ANTES de importar)

# 4. Importar
portablecode import mi-config.portablecode --force

# 5. Si incluiste engram/gentle-ai (--include-engram):
#    a) Instalar gentle-ai/engram en la PC nueva (si no esta)
#    b) Parar engram, renombrar el archivo staging:
#       move "C:\Users\...\engram-import.db" "C:\Users\...\engram.db"
#    c) Reiniciar engram y OpenCode

# 6. Reiniciar OpenCode
```

## Features

- **Clasificacion por tiers**: Archivos categorizados en 5 niveles segun como se manejan
- **Transformacion de paths**: Reemplaza rutas hardcoded de usuario por `{HOME}` (cross-platform)
- **Soporte multiplataforma**: Windows, Linux, macOS
- **Formato archive**: tar.gz con manifest.json para metadata
- **Diff**: Compara configuracion actual contra un backup

## File Tiers

| Tier | Nombre | Que incluye | Que hace |
|------|--------|-------------|----------|
| 1 | Copy as-is | AGENTS.md, skills/, plugins/, commands/, imagenes | Copia sin modificar |
| 2 | Transform | opencode.json, tui.json, opencode-notifier.json | Reemplaza paths con `{HOME}` |
| 3 | Install separately | engram.exe, codebase-memory-mcp.exe | Se salta (instalar manual) |
| 4 | Sensitive | auth.json | Opt-in con `--include-auth` |
| 5 | Skip | node_modules/, lock files, opencode.db | Se excluye siempre |

> **Engram/gentle-ai**: Usá `--include-engram` para incluir la base de datos de memoria persistente. Se exporta como Tier 2 (transform) automáticamente — los paths absolutos se reemplazan por `{HOME}`.

## Estructura del proyecto

```
portablecode/
├── __init__.py      # Version del paquete
├── types.py         # Dataclasses y constantes (Tier, FileEntry, etc.)
├── paths.py         # Utilidades de paths (config dir, data dir, plataforma)
├── discover.py      # Descubrimiento de archivos + clasificacion por tier
├── transform.py     # Transformacion de paths ({HOME} ↔ rutas reales)
├── archive.py       # Creacion/extraccion de tar.gz con manifest
└── cli.py           # CLI con click (export, import, list, diff)
pyproject.toml       # Config del paquete
```

## Desarrollo

```bash
# Instalar en modo dev
pip install -e .

# Ejecutar directamente
python -m portablecode.cli list
python -m portablecode.cli export -o test.portablecode

# Limpiar bytecode
find . -type d -name __pycache__ -exec rm -rf {} +
```

## License

MIT
