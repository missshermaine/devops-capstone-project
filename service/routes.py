"""REST endpoints for the Accounts service."""
from flask import jsonify, request, make_response, abort, url_for
from service.models import Account
from service.common import status
from . import app


@app.route("/health")
def health():
    """Report service health."""
    return jsonify(status="OK"), status.HTTP_200_OK


@app.route("/")
def index():
    """Describe the service."""
    return jsonify(
        name="Account REST API Service",
        version="1.0",
        paths=url_for("list_accounts", _external=True),
    ), status.HTTP_200_OK


@app.route("/accounts", methods=["POST"])
def create_accounts():
    """Create an account and return its resource location."""
    account = read_account_data()
    account.create()
    location = url_for("get_accounts", account_id=account.id, _external=True)
    return make_response(
        jsonify(account.serialize()), status.HTTP_201_CREATED,
        {"Location": location},
    )


@app.route("/accounts", methods=["GET"])
def list_accounts():
    """List all accounts."""
    return jsonify([account.serialize() for account in Account.all()]), status.HTTP_200_OK


@app.route("/accounts/<int:account_id>", methods=["GET"])
def get_accounts(account_id):
    """Read one account or return 404."""
    account = find_account(account_id)
    return jsonify(account.serialize()), status.HTTP_200_OK


@app.route("/accounts/<int:account_id>", methods=["PUT"])
def update_accounts(account_id):
    """Validate all update data before changing the saved account."""
    account = find_account(account_id)
    updated = read_account_data()
    for field in ("name", "email", "address", "phone_number", "date_joined"):
        setattr(account, field, getattr(updated, field))
    account.update()
    return jsonify(account.serialize()), status.HTTP_200_OK


@app.route("/accounts/<int:account_id>", methods=["DELETE"])
def delete_accounts(account_id):
    """Delete an account; repeated deletion also returns 204."""
    account = Account.find(account_id)
    if account is not None:
        account.delete()
    return "", status.HTTP_204_NO_CONTENT


def find_account(account_id):
    """Find an account and reject an unknown resource ID."""
    account = Account.find(account_id)
    if account is None:
        abort(status.HTTP_404_NOT_FOUND, f"Account {account_id} was not found")
    return account


def read_account_data():
    """Read and validate a JSON account without modifying saved data."""
    check_content_type("application/json")
    data = request.get_json()
    if not isinstance(data, dict):
        abort(status.HTTP_400_BAD_REQUEST, "Account data must be a JSON object")
    try:
        return Account().deserialize(data)
    except ValueError:
        abort(status.HTTP_400_BAD_REQUEST, "date_joined must be a valid ISO date")


def check_content_type(media_type):
    """Require the expected request media type."""
    if request.mimetype != media_type:
        abort(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Content-Type must be {media_type}")
