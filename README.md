# MYRIAD Multi-Risk Toolkit

## Development

### Recommended VSCode settings

#### [.vscode/launch.json](.vscode/launch.json)

```json
{
  "configurations": [
    {
      "name": "Debug Django (all)",
      "type": "debugpy",
      "request": "launch",
      "args": [
        "runserver"
      ],
      "django": true,
      "autoStartBrowser": false,
      "program": "${workspaceFolder}/manage.py",
      "justMyCode": false
    },
    {
      "name": "Debug Django (mine)",
      "type": "debugpy",
      "request": "launch",
      "args": [
        "runserver"
      ],
      "django": true,
      "autoStartBrowser": false,
      "program": "${workspaceFolder}/manage.py",
      "justMyCode": true
    }
  ]
}
```
