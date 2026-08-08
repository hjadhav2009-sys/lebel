import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Boxes, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Columns3, FileClock, FileUp, Gauge, Import, Menu, Moon, PackageCheck, PanelRightClose, Printer, Search, Settings, ShieldCheck, SlidersHorizontal, Sun, UploadCloud, Users, X } from "lucide-react";
import { sampleProducts } from "./data";
import type { Product } from "./types";

const nav = [
  ["Dashboard", Gauge], ["Inventory", Boxes], ["Consignments", PackageCheck], ["Print Queue", Printer],
  ["Imports", Import], ["Errors", AlertTriangle], ["Accounts", Users], ["Settings", Settings], ["Admin", ShieldCheck],
] as const;

const allColumns = ["Marketplace", "Account", "SKU", "Identifiers", "Title", "Brand", "MRP", "Category", "Image Status", "Updated"];

function App() {
  const [products, setProducts] = useState<Product[]>(sampleProducts);
  const [active, setActive] = useState("Inventory");
  const [theme, setTheme] = useState<"light" | "dark">((localStorage.getItem("mms-theme") as "light" | "dark") || "light");
  const [market, setMarket] = useState("All marketplaces");
  const [account, setAccount] = useState("All accounts");
  const [category, setCategory] = useState("All categories");
  const [imageStatus, setImageStatus] = useState("All images");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [drawer, setDrawer] = useState<Product | null>(null);
  const [density, setDensity] = useState<"compact" | "comfortable">("compact");
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [visible, setVisible] = useState(new Set(allColumns));
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("mms-theme", theme); }, [theme]);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/v1/products?page=1&page_size=200", { signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((page) => setProducts(page.items.map((item: any) => {
        const ids = Object.fromEntries(item.identifiers.map((identifier: any) => [identifier.kind, identifier.value]));
        return { id: item.id, marketplace: item.account.marketplace === "amazon" ? "Amazon" : "Flipkart", account: item.account.name, sku: item.sku || "—", asin: ids.asin, fnsku: ids.fnsku, fsn: ids.fsn, title: item.title || "Untitled product", brand: item.brand || "—", mrp: item.mrp == null ? undefined : Number(item.mrp), category: item.category || "Uncategorized", image: item.images[0]?.url, updated: new Date(item.updated_at).toLocaleDateString("en-IN"), source: item.source_file || "Unknown source" } as Product;
      })))
      .catch(() => { /* Keep representative local data when the API is not running. */ });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "/" && document.activeElement?.tagName !== "INPUT") { event.preventDefault(); searchRef.current?.focus(); }
      if (event.key === "Escape") setDrawer(null);
    };
    window.addEventListener("keydown", handler); return () => window.removeEventListener("keydown", handler);
  }, []);

  const filtered = useMemo(() => products.filter((p) => {
    const haystack = [p.sku, p.asin, p.fnsku, p.fsn, p.title, p.brand].join(" ").toLowerCase();
    return (market === "All marketplaces" || p.marketplace === market) && (account === "All accounts" || p.account === account) && (category === "All categories" || p.category === category) && (imageStatus === "All images" || (imageStatus === "Available" ? !!p.image : !p.image)) && haystack.includes(search.toLowerCase());
  }), [products, market, account, category, imageStatus, search]);

  const toggleAll = () => setSelected(selected.size === filtered.length ? new Set() : new Set(filtered.map((p) => p.id)));
  const toggle = (id: string) => setSelected((old) => { const next = new Set(old); next.has(id) ? next.delete(id) : next.add(id); return next; });

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">M</div><div><strong>MMS</strong><span>Catalog workspace</span></div></div>
      <nav>{nav.map(([label, Icon]) => <button className={active === label ? "active" : ""} key={label} onClick={() => setActive(label)}><Icon size={18}/><span>{label}</span>{label === "Errors" && <em>3</em>}</button>)}</nav>
      <div className="sidebar-foot"><button><CircleHelp size={18}/><span>Help & support</span></button><div className="version">MMS Web · Phase 1</div></div>
    </aside>

    <main>
      <header className="topbar">
        <button className="mobile-menu"><Menu size={20}/></button>
        <div className="context-select"><span>Marketplace</span><button>{market === "All marketplaces" ? "All" : market}<ChevronDown size={14}/></button></div>
        <div className="context-select"><span>Account</span><button>{account === "All accounts" ? "All accounts" : account}<ChevronDown size={14}/></button></div>
        <div className="global-search"><Search size={17}/><input ref={searchRef} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search SKU, ASIN, FNSKU, FSN or title…"/><kbd>/</kbd></div>
        <button className="icon-button" aria-label="Toggle color theme" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>{theme === "light" ? <Moon size={18}/> : <Sun size={18}/>}</button>
        <div className="user"><div>AK</div><span><strong>Arun Kumar</strong><small>Administrator</small></span><ChevronDown size={14}/></div>
      </header>

      {active === "Inventory" ? <section className="content">
        <div className="page-heading"><div><p className="eyebrow">CATALOG</p><h1>Inventory</h1><p>One reliable view of every product across your marketplace accounts.</p></div><button className="primary" onClick={() => setActive("Imports")}><FileUp size={17}/>Import catalog</button></div>
        <div className="stats"><span><strong>20,248</strong> total products</span><i></i><span><b className="green-dot"></b><strong>18,942</strong> with images</span><i></i><span><b className="amber-dot"></b><strong>1,306</strong> need images</span><i></i><span>Last import <strong>12 min ago</strong></span></div>
        <div className="toolbar">
          <Select value={market} setValue={setMarket} label="Marketplace" options={["All marketplaces", "Amazon", "Flipkart"]}/>
          <Select value={account} setValue={setAccount} label="Account" options={["All accounts", "Mumbai Seller", "Bangalore Account", "Account 1", "Account 2"]}/>
          <Select value={category} setValue={setCategory} label="Category" options={["All categories", ...Array.from(new Set(products.map((p) => p.category)))]}/>
          <Select value={imageStatus} setValue={setImageStatus} label="Images" options={["All images", "Available", "Missing"]}/>
          <button className="tool-button"><SlidersHorizontal size={16}/>More filters</button>
          <div className="toolbar-spacer"/>
          <button className="tool-button" onClick={() => setDensity(density === "compact" ? "comfortable" : "compact")}>{density === "compact" ? "Compact" : "Comfortable"}</button>
          <div className="popover-wrap"><button className="tool-button" onClick={() => setColumnsOpen(!columnsOpen)}><Columns3 size={16}/>Columns</button>{columnsOpen && <div className="column-popover"><strong>Visible columns</strong>{allColumns.map((c) => <label key={c}><input type="checkbox" checked={visible.has(c)} onChange={() => setVisible((old) => { const next = new Set(old); next.has(c) ? next.delete(c) : next.add(c); return next; })}/>{c}</label>)}</div>}</div>
        </div>
        {selected.size > 0 && <div className="selection-bar"><strong>{selected.size} selected</strong><button>Export selected</button><button>Add to consignment</button><button onClick={() => setSelected(new Set())}><X size={15}/>Clear</button></div>}
        <div className={`table-card ${density}`} role="region" aria-label="Product inventory" tabIndex={0}>
          <table><thead><tr><th className="check"><input aria-label="Select visible products" type="checkbox" checked={filtered.length > 0 && selected.size === filtered.length} onChange={toggleAll}/></th><th className="thumb">Image</th>{visible.has("Marketplace") && <th>Marketplace</th>}{visible.has("Account") && <th>Account</th>}{visible.has("SKU") && <th>SKU</th>}{visible.has("Identifiers") && <th>ASIN / FNSKU / FSN</th>}{visible.has("Title") && <th className="title-col">Product</th>}{visible.has("Brand") && <th>Brand</th>}{visible.has("MRP") && <th className="money">MRP</th>}{visible.has("Category") && <th>Category</th>}{visible.has("Image Status") && <th>Images</th>}{visible.has("Updated") && <th>Updated</th>}</tr></thead>
            <tbody>{filtered.map((p) => <tr key={p.id} className={selected.has(p.id) ? "selected" : ""} onClick={() => setDrawer(p)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && setDrawer(p)}><td className="check" onClick={(e) => e.stopPropagation()}><input aria-label={`Select ${p.sku}`} type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)}/></td><td className="thumb">{p.image ? <img src={p.image} alt=""/> : <div className="image-empty"><Boxes size={17}/></div>}</td>{visible.has("Marketplace") && <td><Badge market={p.marketplace}/></td>}{visible.has("Account") && <td>{p.account}</td>}{visible.has("SKU") && <td><code>{p.sku}</code></td>}{visible.has("Identifiers") && <td><div className="identifiers">{p.asin && <span><small>ASIN</small>{p.asin}</span>}{p.fnsku && <span><small>FNSKU</small>{p.fnsku}</span>}{p.fsn && <span><small>FSN</small>{p.fsn}</span>}</div></td>}{visible.has("Title") && <td className="product-title"><strong>{p.title}</strong><small>{p.category}</small></td>}{visible.has("Brand") && <td>{p.brand}</td>}{visible.has("MRP") && <td className="money">{p.mrp ? `₹${p.mrp.toLocaleString("en-IN")}` : <span className="missing">Missing</span>}</td>}{visible.has("Category") && <td><span className="category">{p.category}</span></td>}{visible.has("Image Status") && <td>{p.image ? <span className="status available">Available</span> : <span className="status missing-status">Missing</span>}</td>}{visible.has("Updated") && <td className="muted">{p.updated}</td>}</tr>)}</tbody></table>
          {filtered.length === 0 && <div className="empty"><Search size={30}/><strong>No products found</strong><p>Try clearing a filter or changing your search.</p></div>}
        </div>
        <div className="pagination"><span>Showing <strong>1–{filtered.length}</strong> of <strong>20,248</strong></span><div><button disabled><ChevronLeft size={16}/></button><button className="page-active">1</button><button>2</button><button>3</button><span>…</span><button>405</button><button><ChevronRight size={16}/></button></div><label>Rows <select><option>50</option><option>100</option><option>200</option></select></label></div>
      </section> : active === "Imports" ? <Imports onBack={() => setActive("Inventory")}/> : <Placeholder name={active}/>}
    </main>
    {drawer && <ProductDrawer product={drawer} close={() => setDrawer(null)}/>}
  </div>;
}

function Select({ value, setValue, label, options }: { value: string; setValue: (v: string) => void; label: string; options: string[] }) {
  return <label className="select-control"><span>{label}</span><select value={value} onChange={(e) => setValue(e.target.value)}>{options.map((o) => <option key={o}>{o}</option>)}</select><ChevronDown size={14}/></label>;
}

function Badge({ market }: { market: Product["marketplace"] }) { return <span className={`badge ${market.toLowerCase()}`}><b>{market === "Amazon" ? "a" : "f"}</b>{market}</span>; }

function ProductDrawer({ product: p, close }: { product: Product; close: () => void }) {
  return <><button className="backdrop" aria-label="Close details" onClick={close}/><aside className="drawer" aria-label="Product details"><header><div><p>PRODUCT DETAILS</p><h2>{p.sku}</h2></div><button className="icon-button" onClick={close}><PanelRightClose size={20}/></button></header><div className="drawer-body"><div className="gallery">{p.image ? <img src={p.image} alt={p.title}/> : <div><Boxes size={38}/><span>No image available</span></div>}<span className={`status ${p.image ? "available" : "missing-status"}`}>{p.image ? "Image available" : "Needs enrichment"}</span></div><div className="drawer-title"><Badge market={p.marketplace}/><h3>{p.title}</h3><p>{p.brand}</p></div><dl><div><dt>Account</dt><dd>{p.account}</dd></div><div><dt>MRP</dt><dd>{p.mrp ? `₹${p.mrp.toLocaleString("en-IN")}` : "Not provided"}</dd></div><div><dt>Category</dt><dd>{p.category}</dd></div><div><dt>SKU</dt><dd><code>{p.sku}</code></dd></div>{p.asin && <div><dt>ASIN</dt><dd><code>{p.asin}</code></dd></div>}{p.fnsku && <div><dt>FNSKU</dt><dd><code>{p.fnsku}</code></dd></div>}{p.fsn && <div><dt>FSN</dt><dd><code>{p.fsn}</code></dd></div>}<div><dt>Source file</dt><dd>{p.source}</dd></div><div><dt>Last updated</dt><dd>{p.updated}</dd></div></dl><div className="drawer-tabs"><button className="active">Change history</button><button>Images</button><button>Print history</button></div><div className="timeline"><i></i><div><strong>Catalog record updated</strong><p>MRP changed from ₹749 to ₹{p.mrp}</p><small>Today · Import job #IMP-0248</small></div><i></i><div><strong>Product created</strong><p>Added from {p.source}</p><small>18 Jul 2026</small></div></div></div></aside></>;
}

function Imports({ onBack }: { onBack: () => void }) {
  const [files, setFiles] = useState<string[]>(["0_APPAREL_PIN-KEYCHAIN.xlsm", "Quality_Check_key_chain.csv"]);
  const add = (list: FileList | null) => list && setFiles((old) => [...old, ...Array.from(list).map((f) => f.name)]);
  return <section className="content"><div className="page-heading"><div><p className="eyebrow">CATALOG</p><h1>Import catalog</h1><p>Upload marketplace files. Headers are detected by technical keys and aliases.</p></div><button className="secondary" onClick={onBack}>Back to inventory</button></div><label className="dropzone" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); add(e.dataTransfer.files); }}><input type="file" multiple accept=".csv,.xlsx,.xlsm" onChange={(e) => add(e.target.files)}/><UploadCloud size={32}/><strong>Drop catalog files here</strong><p>or click to select CSV, XLSX, or XLSM files</p><span>Multiple Amazon templates can be merged into one account.</span></label><div className="import-card"><header><div><strong>Files ready for review</strong><span>{files.length} detected</span></div><button className="primary" disabled={!files.length}>Review & import</button></header><table><thead><tr><th>File</th><th>Marketplace</th><th>Account</th><th>Detected type</th><th>Rows</th><th>Mapping</th></tr></thead><tbody>{files.map((file, i) => <tr key={`${file}-${i}`}><td><div className="file-cell"><FileClock size={18}/><span><strong>{file}</strong><small>{file.endsWith(".csv") ? "CSV" : "Excel workbook"}</small></span></div></td><td><Badge market={file.includes("Quality") ? "Flipkart" : "Amazon"}/></td><td>{file.includes("Quality") ? "Account 1" : "Mumbai Seller"}</td><td>{file.includes("Quality") ? "Flipkart QC Catalog" : "Amazon Listing Template"}</td><td>{i ? "2,416" : "8,972"}</td><td><span className="status available">Ready</span></td></tr>)}</tbody></table></div><div className="import-summary"><div><span>NEW</span><strong>200</strong><small>products to add</small></div><div><span>UPDATED</span><strong>31</strong><small>changed records</small></div><div><span>UNCHANGED</span><strong>11,157</strong><small>left untouched</small></div><div><span>ERRORS</span><strong className="error-text">0</strong><small>blocking issues</small></div></div></section>;
}

function Placeholder({ name }: { name: string }) { return <section className="content"><div className="page-heading"><div><p className="eyebrow">MMS WORKSPACE</p><h1>{name}</h1><p>This module is scaffolded for a later migration phase.</p></div></div><div className="placeholder"><ShieldCheck size={36}/><strong>{name} foundation ready</strong><p>Phase 1 keeps focus on catalog imports and Inventory.</p></div></section>; }

export default App;
