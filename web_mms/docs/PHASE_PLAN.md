# MMS Web phase plan

## Phase 1 — catalog foundation

PostgreSQL entities, normalized imports, account boundaries, audit records, and the initial React workspace.

## Phase 1.5 — foundation hardening and catalog operations

Explicit migration, source-aware synchronization, marketplace identity policy, row savepoints, workbook and formula safety, file fingerprints, catalog batches, server-side Inventory, Product Drawer, Import Center, Accounts, Errors, CI, and tool boundaries.

## Phase 2 — consignments

Amazon and Flipkart To Print, Printed/Reprint, quantity resolution, inline validation, and structured errors. Printing remains simulated/durable only.

## Phase 3 — print agent and renderers

Outbound Windows agent, printer profiles, spooler integration, and parity-tested migration of existing renderers.

## Phase 4 — packing and PDF tools

Adapters for the legacy packing/order parser and Flipkart PDF cropper after parity tests.
# Phase 2 — Consignment Operations

Phase 2 adds Amazon/Flipkart consignment sessions, account-scoped matching, structured validation, independent row overrides, operational address and label-format profiles, immutable print-job preparation, Print Queue, Printed/Reprint history, optimistic concurrency, and development-only completion simulation.

It deliberately does not migrate desktop label rendering, raw PRN/TSPL transport, browser-direct printing, the packing parser, or PyMuPDF cropper logic. Those remain behind documented adapter boundaries. Phase 3 will connect prepared immutable jobs to an authenticated local printer agent and the validated renderer.

Core distinctions: Catalog is not Consignment; Net Quantity is not Print Quantity; Prepared is not Printed; Reprint creates a new job; a new consignment starts fresh even when its source file and products appeared before.
