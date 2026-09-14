from flask import Blueprint, redirect, render_template, request, url_for

from app import store
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.transaction import Transaction

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def home():
    return render_template("home.html")


@views_bp.route("/ui/products", methods=["GET", "POST"])
def products_page():
    if request.method == "POST":
        product_id = store.next_id("product")
        product = Product(
            id=product_id,
            name=request.form["name"],
            sku=request.form["sku"],
            unit_price=float(request.form["unit_price"]),
            quantity_on_hand=int(request.form["quantity_on_hand"]),
        )
        store.products[product_id] = product
        return redirect(url_for("views.products_page"))
    return render_template("products.html", products=store.products.values())


@views_bp.route("/ui/products/<int:product_id>/delete", methods=["POST"])
def delete_product_page(product_id):
    store.products.pop(product_id, None)
    return redirect(url_for("views.products_page"))


@views_bp.route("/ui/suppliers", methods=["GET", "POST"])
def suppliers_page():
    if request.method == "POST":
        supplier_id = store.next_id("supplier")
        supplier = Supplier(
            id=supplier_id,
            name=request.form["name"],
            contact_email=request.form["contact_email"],
        )
        store.suppliers[supplier_id] = supplier
        return redirect(url_for("views.suppliers_page"))
    return render_template("suppliers.html", suppliers=store.suppliers.values())


@views_bp.route("/ui/suppliers/<int:supplier_id>/delete", methods=["POST"])
def delete_supplier_page(supplier_id):
    store.suppliers.pop(supplier_id, None)
    return redirect(url_for("views.suppliers_page"))


@views_bp.route("/ui/transactions", methods=["GET", "POST"])
def transactions_page():
    if request.method == "POST":
        product_id = int(request.form["product_id"])
        tx_type = request.form["type"]
        quantity = int(request.form["quantity"])
        supplier_id = request.form.get("supplier_id") or None
        if supplier_id:
            supplier_id = int(supplier_id)

        product = store.products.get(product_id)
        if product is not None:
            if tx_type == "IN":
                product.quantity_on_hand += quantity
            elif tx_type == "OUT":
                product.quantity_on_hand -= quantity

            transaction_id = store.next_id("transaction")
            transaction = Transaction(
                id=transaction_id,
                product_id=product_id,
                supplier_id=supplier_id,
                type=tx_type,
                quantity=quantity,
            )
            store.transactions[transaction_id] = transaction
        return redirect(url_for("views.transactions_page"))
    return render_template("transactions.html", transactions=store.transactions.values())
