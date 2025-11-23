' VBScript wrapper to run emergency alert completely silently
' This script is completely invisible - no windows, no output, no traces

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Find pythonw.exe in the parent directory's .venv
pythonwExe = scriptDir & "\..\.venv\Scripts\pythonw.exe"

' If pythonw.exe doesn't exist, try python.exe
If Not fso.FileExists(pythonwExe) Then
    pythonwExe = scriptDir & "\..\.venv\Scripts\python.exe"
End If

' Find the trigger_emergency.py script
triggerScript = scriptDir & "\trigger_emergency.py"

' Run the script completely silently
' 0 = Hidden window (completely invisible)
' False = Don't wait for completion (fire and forget)
WshShell.Run """" & pythonwExe & """ """ & triggerScript & """", 0, False

' Clean up and exit silently
Set WshShell = Nothing
Set fso = Nothing

