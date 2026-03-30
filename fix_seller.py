import re

filepath = r"frontend/index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the product card section (around line 894)
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "let p_html = '';" in line and start_idx is None and i > 850:
        start_idx = i
    if start_idx and "document.getElementById('sellerProductList').innerHTML" in line and i > start_idx:
        end_idx = i + 1
        break

print(f"Found product card section: lines {start_idx+1} to {end_idx}")

new_product_section = """                let p_html = '';
                products.forEach(p => {
                    const sc = p.status === 'Active' ? 'text-emerald-500 bg-emerald-50' : 'text-slate-400 bg-slate-100';
                    const eName = p.name.replace(/'/g,"\\\\'");
                    const eDesc = (p.description||'').replace(/'/g,"\\\\'");
                    p_html += `
                        <div class="glass-card p-3 flex justify-between items-center">
                            <div class="flex items-center gap-3">
                                <img src="${p.image}" class="w-10 h-10 rounded-lg object-cover">
                                <div><h4 class="text-xs font-bold">${p.name}</h4><p class="text-[10px] text-slate-500">\\u20b9${p.price}</p></div>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="text-[8px] font-bold ${sc} px-2 py-0.5 rounded uppercase">${p.status}</span>
                                <button onclick="editProduct('${p._id}', '${eName}', ${p.price}, '${eDesc}', '${p.status}')" class="w-7 h-7 rounded-lg bg-slate-100 text-slate-500 flex items-center justify-center hover:bg-primary hover:text-white transition text-[10px]"><i class="fa-solid fa-pen"></i></button>
                                <button onclick="deleteProduct('${p._id}', '${eName}')" class="w-7 h-7 rounded-lg bg-red-50 text-red-400 flex items-center justify-center hover:bg-red-500 hover:text-white transition text-[10px]"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </div>`;
                });
                document.getElementById('sellerProductList').innerHTML = p_html || '<p class="text-xs text-slate-400">No listings yet.</p>';
"""

if start_idx is not None and end_idx is not None:
    lines[start_idx:end_idx] = [new_product_section]

# Now find collectPayment and update the "Confirm Delivery" button 
# to also auto-collect payment
# Find the seller order buttons section and update "Confirm Delivery" to auto-pay
content = ''.join(lines)

# Replace the separate Confirm Delivery and Collect buttons with a single "Deliver & Collect" flow
# When seller marks Delivered, it auto-collects payment
old_deliver = """${o.status === 'Shipped' ? `<button onclick="updateOrderStatus('${o._id}', 'Delivered')" class="flex-1 bg-emerald-50 text-emerald-600 font-bold text-[9px] py-1.5 rounded-lg border border-emerald-100">Confirm Delivery</button>` : ''}
                                ${o.status === 'Delivered' && !isPaid ? `<button onclick="collectPayment('${o._id}')" class="flex-1 bg-primary text-white font-bold text-[9px] py-1.5 rounded-lg shadow-sm">Collect"""

new_deliver = """${o.status === 'Shipped' ? `<button onclick="deliverAndCollect('${o._id}')" class="flex-1 bg-emerald-50 text-emerald-600 font-bold text-[9px] py-1.5 rounded-lg border border-emerald-100">Deliver & Collect</button>` : ''}
                                ${o.status === 'Delivered' && !isPaid ? `<button onclick="collectPayment('${o._id}')" class="flex-1 bg-primary text-white font-bold text-[9px] py-1.5 rounded-lg shadow-sm">Collect"""

content = content.replace(old_deliver, new_deliver)

# Add edit/delete functions after collectPayment function
old_collect_end = """                showToast("Payment recorded!", "Success");
                loadSellerDashboard();
            });
        }"""

new_collect_end = """                showToast("Payment recorded!", "Success");
                loadSellerDashboard();
            });
        }
        async function deliverAndCollect(id) {
            showConfirm("Deliver & Collect Payment", "Mark as delivered and confirm payment received?", async () => {
                await fetch(`${API_URL}/marketplace/orders/${id}/status`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({status: 'Delivered'})});
                await fetch(`${API_URL}/marketplace/orders/${id}/pay`, {method: 'PUT', headers: {'Content-Type': 'application/json'}});
                showToast("Delivered & payment collected!", "Success");
                loadSellerDashboard();
            });
        }
        function editProduct(id, name, price, desc, status) {
            document.getElementById('epId').value = id;
            document.getElementById('epName').value = name;
            document.getElementById('epPrice').value = price;
            document.getElementById('epDesc').value = desc;
            document.getElementById('epStatus').value = status;
            document.getElementById('editProductModal').classList.remove('hidden');
        }
        document.getElementById('editProductForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('epId').value;
            await fetch(`${API_URL}/marketplace/products/${id}`, {
                method: 'PUT', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: document.getElementById('epName').value,
                    price: document.getElementById('epPrice').value,
                    description: document.getElementById('epDesc').value,
                    status: document.getElementById('epStatus').value
                })
            });
            document.getElementById('editProductModal').classList.add('hidden');
            showToast("Product updated!", "Success");
            loadSellerDashboard();
        });
        async function deleteProduct(id, name) {
            showConfirm("Delete Product", `Remove "${name}" from your store?`, async () => {
                await fetch(`${API_URL}/marketplace/products/${id}`, {method: 'DELETE'});
                showToast("Product deleted.", "Success");
                loadSellerDashboard();
            });
        }"""

content = content.replace(old_collect_end, new_collect_end)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Updated seller product cards, delivery+payment flow, and edit/delete functions.")
