from flask import Blueprint, jsonify, request

from app import store
from app.models.renter import Renter

renters_bp = Blueprint("renters", __name__, url_prefix="/renters")


@renters_bp.route("", methods=["GET"])
def list_renters():
    return jsonify([r.to_dict() for r in store.renters.values()])


@renters_bp.route("", methods=["POST"])
def create_renter():
    data = request.get_json()
    renter_id = store.next_id("renter")
    renter = Renter(id=renter_id, name=data["name"], email=data["email"])
    store.renters[renter_id] = renter
    return jsonify(renter.to_dict()), 201


@renters_bp.route("/<int:renter_id>", methods=["GET"])
def get_renter(renter_id):
    renter = store.renters.get(renter_id)
    if renter is None:
        return jsonify({"error": "Renter not found"}), 404
    return jsonify(renter.to_dict())


@renters_bp.route("/<int:renter_id>", methods=["PUT"])
def update_renter(renter_id):
    renter = store.renters.get(renter_id)
    if renter is None:
        return jsonify({"error": "Renter not found"}), 404
    data = request.get_json()
    renter.name = data.get("name", renter.name)
    renter.email = data.get("email", renter.email)
    return jsonify(renter.to_dict())


@renters_bp.route("/<int:renter_id>", methods=["DELETE"])
def delete_renter(renter_id):
    renter = store.renters.pop(renter_id, None)
    if renter is None:
        return jsonify({"error": "Renter not found"}), 404
    return "", 204
