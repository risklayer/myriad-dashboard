# MYRIAD-EU Multi-Risk Toolkit

## Development

Before starting development, you will need to install both python and nodejs.

Then run:

```sh
./tools/provision.sh
```

### Building JavaScript files in development

This will watch for any changes to js files that are compiled:

```sh
npm run start
```

### Recommended VSCode settings

### MacOS

Ensure you're using python 3.12 or higher.

Install Homebrew (if not already installed):

```zsh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install GDAL:

```zsh
brew install gdal
```

Update your settings so python can find GDAL and GEOS (confirm these paths are
correct for your machine first):

```py
GDAL_LIBRARY_PATH = "/opt/homebrew/opt/gdal/lib/libgdal.dylib"
GEOS_LIBRARY_PATH = "/opt/homebrew/opt/geos/lib/libgeos_c.dylib"
```

To use Spatialite for your DB:

```zsh
brew install libspatialite
```

#### [.vscode/launch.json](.vscode/launch.json)

```json
{
  "configurations": [
    {
      "name": "Debug Django (all)",
      "type": "debugpy",
      "request": "launch",
      "args": ["runserver"],
      "django": true,
      "autoStartBrowser": false,
      "program": "${workspaceFolder}/manage.py",
      "justMyCode": false
    },
    {
      "name": "Debug Django (mine)",
      "type": "debugpy",
      "request": "launch",
      "args": ["runserver"],
      "django": true,
      "autoStartBrowser": false,
      "program": "${workspaceFolder}/manage.py",
      "justMyCode": true
    }
  ]
}
```
