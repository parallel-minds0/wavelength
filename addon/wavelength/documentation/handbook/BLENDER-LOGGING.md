# Blender diagnostics

Open the wavelength sidebar and expand **Diagnostics**.

- **View Log** shows the current log snapshot in Blender's Text Editor. Press
  Shift-F5 to return to the 3D View. Open View Log again to refresh the snapshot.
- **Export Log** saves the current log to a chosen file for troubleshooting.
- The latest captured error and active log path appear in the panel.

Logs are stored beneath Blender's user configuration directory in
`wavelength/logs/wavelength.log`. They survive add-on reloads and Blender restarts.
Rotation retains the active 2 MiB log and three backups. Error references connect
the short on-screen message with the timestamped traceback in the log.

Captured events include shared map-authoring operators, map compilation failures,
build monitor exceptions, primitive and asset operations, and add-on registration failures. Compiler-specific
output remains available through the existing Build Logs control. This is not a
capture of Blender's entire console or native crashes.

Logs can contain local paths and exception details. Export is manual; nothing is
uploaded automatically. The installer CLI is unchanged.
