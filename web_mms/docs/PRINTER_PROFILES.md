# Printer profiles

A profile belongs to one discovered Windows printer and a marketplace, optionally one marketplace account. It records media width/height, gap, speed, darkness, renderer key, renderer configuration, and monotonically increasing layout version. DPI comes from the printer and must equal the profile's approved DPI.

Profiles are operational contracts, not cosmetic preferences. Update through the API/UI so layout version and audit history advance. Existing artifacts retain their original profile and renderer identity. Disable printers that should not receive claims.
