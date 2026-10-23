# Lifecycles, context and cleanup

## Context capabilities

The scene context supports editing, clean preview and suspension. Workspace
activation is an additional gate. Rendering excludes editor helpers independently
of the active workspace, and restores previous user flags afterward. Query the
capability policy rather than checking a workspace label in every operator.

```{code-sample} addon/wavelength/source/context_policy.py capability-policy
```

`context_state.py` performs Blender visibility changes and stores reversible
state. `context_policy.py` classifies intent and capabilities. Preserve this
separation when adding a new helper or render behavior.

## Asset setup lifecycle

Configuration settles before indexing/preparation begins. A hidden worker reads
game content and writes previews. The editor polls bounded results and attaches
pixels to matching catalog assets. Pause/cancel retain completed cache work.
Failure of one asset must not discard unrelated successful previews.

## Modal sessions

A Blender operator is a temporary RNA object. Undo, reload or cancellation can
invalidate it. Asset placement keeps resources in a plain `PlacementSession`,
checks operator validity and cleans up on undo/redo/load. Timers, draw handlers,
cursor overrides and status text need one cleanup path. Do not retain a removed
operator as the lifetime owner of those resources.

```{code-sample} addon/wavelength/source/asset_placement.py session-recovery
```

## Compiler pipeline

The pipeline polls subprocesses without blocking Blender. Commands are argument
lists rather than shell strings. Terminal states do not restart work; timeout
and cancellation close logs and stop the current process. Publish the chosen BSP
only after successful compilation.

```{code-sample} addon/wavelength/source/build/pipeline.py pipeline-poll
```
