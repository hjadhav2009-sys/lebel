# Address Profiles

Address profiles belong to one marketplace account. They hold profile name, marketed/manufactured-by text, two address lines, city/state, email, phone, origin, active state, and default state. An account points to its default profile, while an individual consignment line may override it.

Amazon and Flipkart addresses remain isolated because reads and writes require the owning account ID. No business address is hardcoded. Seed or sample addresses belong only in development fixtures.

Label format profiles may be global or account-specific and store business metadata only: key, display name, marketplace, generic name, required fields, field order, config, and active state. Renderer coordinates remain out of scope.
