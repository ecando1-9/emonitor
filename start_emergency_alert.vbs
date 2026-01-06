' VBScript wrapper to run emergency alert completely silently
' This script is completely invisible - no windows, no output, no traces

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' DEBUG: Verify VBS started
On Error Resume Next
Set debugFile = fso.OpenTextFile(scriptDir & "\app_data\debug_vbs.txt", 8, True)
debugFile.WriteLine "VBS started at " & Now
debugFile.Close
On Error GoTo 0

' Find python.exe (Console version for debugging) in the parent directory's .venv
pythonExecutable = scriptDir & "\..\.venv\Scripts\python.exe"

' If python.exe doesn't exist in venv, try using system command
If Not fso.FileExists(pythonExecutable) Then
    pythonExecutable = "python.exe"
End If

' Find the trigger_emergency.py script
triggerScript = scriptDir & "\trigger_emergency.py"

' Run the script completely silently
' 0 = Hidden window (completely invisible)
' False = Don't wait for completion (fire and forget)
cmd = """" & pythonExecutable & """ """ & triggerScript & """"

On Error Resume Next
Set debugFile = fso.OpenTextFile(scriptDir & "\app_data\debug_vbs.txt", 8, True)
debugFile.WriteLine "Running Command (Silent): " & cmd
debugFile.Close
On Error GoTo 0

WshShell.Run cmd, 0, False

