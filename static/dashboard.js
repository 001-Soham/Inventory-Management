const rowsEl = document.getElementById("product-rows");
const movementEl = document.getElementById("movements");
const productsCache = new Map();

function money(v){ return `$${Number(v || 0).toFixed(2)}`; }

function esc(s){
    return String(s || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

async function loadSummary(){
    if(!document.getElementById("m-products") && !movementEl) return;
    const r = await fetch("/api/dashboard-summary");
    if(!r.ok) return;
    const data = await r.json();
    const m = data.metrics || {};

    if(document.getElementById("m-products")){
        document.getElementById("m-products").textContent = m.total_products ?? 0;
        document.getElementById("m-units").textContent = m.total_units ?? 0;
        document.getElementById("m-value").textContent = money(m.inventory_value ?? 0);
        document.getElementById("m-low").textContent = m.low_stock ?? 0;
    }

    if(movementEl){
        movementEl.innerHTML = (data.recent_movements || []).map(mv => `
            <div class="movement-row">
                <b>${mv.movement_type.toUpperCase()}</b> • ${esc(mv.product_name)} • Qty ${mv.quantity}
                <span>${new Date(mv.created_at).toLocaleString()}</span>
                <small>${esc(mv.note || "-")}</small>
            </div>
        `).join("") || "<p>No movements yet.</p>";
    }
}

function getFilters(){
    const params = new URLSearchParams();
    const qInput = document.getElementById("search");
    const cInput = document.getElementById("filter-category");
    const sInput = document.getElementById("filter-status");
    const query = (qInput?.value || "").trim();
    const category = (cInput?.value || "").trim();
    const status = sInput?.value || "";
    if(query) params.set("query", query);
    if(category) params.set("category", category);
    if(status) params.set("status", status);
    return params.toString();
}

async function loadProducts(){
    if(!rowsEl) return;
    const q = getFilters();
    const r = await fetch(`/api/products${q ? "?" + q : ""}`);
    const products = await r.json();
    productsCache.clear();
    products.forEach(p => productsCache.set(p.id, p));

    rowsEl.innerHTML = products.map(p => `
        <tr>
            <td><input value="${esc(p.sku)}" onchange="quickUpdate(${p.id}, 'sku', this.value)"></td>
            <td><input value="${esc(p.name)}" onchange="quickUpdate(${p.id}, 'name', this.value)"></td>
            <td><input value="${esc(p.category)}" onchange="quickUpdate(${p.id}, 'category', this.value)"></td>
            <td><input value="${esc(p.supplier)}" onchange="quickUpdate(${p.id}, 'supplier', this.value)"></td>
            <td>${p.quantity}</td>
            <td><input type="number" value="${p.reorder_level}" onchange="quickUpdate(${p.id}, 'reorder_level', this.value)"></td>
            <td><input type="number" step="0.01" value="${p.unit_price}" onchange="quickUpdate(${p.id}, 'unit_price', this.value)"></td>
            <td>${money(p.inventory_value)}</td>
            <td>${p.is_low_stock ? '<span class="pill danger">Low</span>' : '<span class="pill ok">Healthy</span>'}</td>
            <td>
                <button onclick="submitMovement('in', ${p.id})">+Stock</button>
                <button onclick="submitMovement('out', ${p.id})">-Stock</button>
                <button class="danger-btn" onclick="delProduct(${p.id})">Delete</button>
            </td>
        </tr>
    `).join("");
}

async function createProduct(){
    const skuEl = document.getElementById("p-sku");
    if(!skuEl) return;
    const body = {
        sku: skuEl.value,
        name: document.getElementById("p-name").value,
        category: document.getElementById("p-category").value,
        supplier: document.getElementById("p-supplier").value,
        unit_price: document.getElementById("p-price").value,
        quantity: document.getElementById("p-qty").value,
        reorder_level: document.getElementById("p-reorder").value
    };

    const r = await fetch("/api/products", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
    const data = await r.json();
    if(data.error) return alert(data.error);
    ["p-sku","p-name","p-category","p-supplier","p-price","p-qty","p-reorder"].forEach(id => document.getElementById(id).value = "");
    loadProducts();
}

async function quickUpdate(id, field, value){
    const existing = productsCache.get(id);
    if(!existing) return;
    const payload = {
        sku: existing.sku,
        name: existing.name,
        category: existing.category,
        supplier: existing.supplier,
        unit_price: existing.unit_price,
        reorder_level: existing.reorder_level
    };
    payload[field] = value;

    const r = await fetch(`/api/products/${id}`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    const data = await r.json();
    if(data.error) return alert(data.error);
    loadProducts();
}

async function loadMovementProducts(){
    const sel = document.getElementById("movement-product");
    if(!sel) return;
    const products = await (await fetch("/api/products")).json();
    sel.innerHTML = products.map(p => `<option value="${p.id}">${esc(p.sku)} - ${esc(p.name)} (Qty: ${p.quantity})</option>`).join("");
}

async function submitMovement(type, directId){
    const productId = directId || document.getElementById("movement-product")?.value;
    const qtyInput = directId ? prompt(`Enter quantity to ${type === 'in' ? 'add' : 'issue'}:`) : document.getElementById("movement-qty")?.value;
    const noteInput = directId ? (prompt("Note (optional)") || "") : (document.getElementById("movement-note")?.value || "");
    if(!productId || !qtyInput) return;

    const r = await fetch(`/api/products/${productId}/movement`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
                body:JSON.stringify({ movement_type:type, quantity:Number(qtyInput), note:noteInput })
    });
    const data = await r.json();
    if(data.error) return alert(data.error);
    alert("Movement recorded");
    if(document.getElementById("movement-qty")) document.getElementById("movement-qty").value = "";
    if(document.getElementById("movement-note")) document.getElementById("movement-note").value = "";
    loadProducts();
    loadMovementProducts();
    loadSummary();
}
async function delProduct(id){
    if(!confirm("Delete this product and all movement history?")) return;
    await fetch(`/api/products/${id}`, { method:"DELETE" });
    loadProducts();
    loadSummary();
}

async function loadLogs(){
    const rows = document.getElementById("log-rows");
    if(!rows) return;
    const type = document.getElementById("log-type")?.value || "";
    const q = type ? `?type=${encodeURIComponent(type)}` : "";
    const logs = await (await fetch(`/api/logs${q}`)).json();
    rows.innerHTML = logs.map(l => `
        <tr>
            <td>${new Date(l.created_at).toLocaleString()}</td>
            <td>${l.movement_type.toUpperCase()}</td>
            <td>${esc(l.sku)}</td>
            <td>${esc(l.product_name)}</td>
            <td>${l.quantity}</td>
            <td>${esc(l.note)}</td>
        </tr>
    `).join("");
}

async function loadProfile(){
    const u = document.getElementById("profile-username");
    if(!u) return;
    const data = await (await fetch("/api/profile")).json();
    u.textContent = data.username;
    document.getElementById("profile-products").textContent = data.products_count;
    document.getElementById("profile-movements").textContent = data.movements_count;
}

async function changePassword(){
    const current_password = document.getElementById("current-password")?.value;
    const new_password = document.getElementById("new-password")?.value;
    const r = await fetch("/api/profile", {
        method:"PUT",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ current_password, new_password })
    });
    const data = await r.json();
    if(data.error) return alert(data.error);
    alert("Password updated successfully");
    document.getElementById("current-password").value = "";
    document.getElementById("new-password").value = "";
}
loadSummary();
loadProducts();
loadMovementProducts();
loadLogs();
loadProfile();
