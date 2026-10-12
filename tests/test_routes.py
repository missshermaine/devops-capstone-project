"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...

    def test_read_account(self):
        """Read all details of an existing account."""
        account = self._create_accounts(1)[0]
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), account.serialize())

    def test_read_missing_account(self):
        """Return 404 for an account that does not exist."""
        response = self.client.get(f"{BASE_URL}/999999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Not Found")

    def test_list_accounts(self):
        """List every saved account and its details."""
        accounts = self._create_accounts(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, 200)
        actual = sorted(response.get_json(), key=lambda item: item["id"])
        expected = sorted(
            [account.serialize() for account in accounts],
            key=lambda item: item["id"],
        )
        self.assertEqual(actual, expected)

    def test_list_empty_accounts(self):
        """Return an empty array when there are no accounts."""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_update_account(self):
        """Save updated details while preserving the resource ID."""
        account = self._create_accounts(1)[0]
        data = AccountFactory().serialize()
        data["id"] = 999999
        response = self.client.put(f"{BASE_URL}/{account.id}", json=data)
        self.assertEqual(response.status_code, 200)
        data["id"] = account.id
        self.assertEqual(response.get_json(), data)
        saved = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(saved.get_json(), data)

    def test_update_missing_account(self):
        """Return 404 when updating a nonexistent account."""
        response = self.client.put(
            f"{BASE_URL}/999999", json=AccountFactory().serialize()
        )
        self.assertEqual(response.status_code, 404)

    def test_update_missing_fields(self):
        """Reject incomplete data without changing the account."""
        account = self._create_accounts(1)[0]
        response = self.client.put(
            f"{BASE_URL}/{account.id}", json={"name": "Changed"}
        )
        self.assertEqual(response.status_code, 400)
        saved = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(saved.get_json(), account.serialize())

    def test_update_wrong_media_type(self):
        """Reject an update that is not JSON."""
        account = self._create_accounts(1)[0]
        response = self.client.put(
            f"{BASE_URL}/{account.id}", data="text", content_type="text/plain"
        )
        self.assertEqual(response.status_code, 415)

    def test_update_invalid_date(self):
        """Reject an invalid date without changing saved details."""
        account = self._create_accounts(1)[0]
        data = account.serialize()
        data["date_joined"] = "not-a-date"
        response = self.client.put(f"{BASE_URL}/{account.id}", json=data)
        self.assertEqual(response.status_code, 400)
        saved = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(saved.get_json(), account.serialize())

    def test_delete_account(self):
        """Delete an account and verify it can no longer be read."""
        account = self._create_accounts(1)[0]
        response = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b"")
        self.assertEqual(
            self.client.get(f"{BASE_URL}/{account.id}").status_code, 404
        )
        self.assertEqual(self.client.get(BASE_URL).get_json(), [])
        self.assertEqual(
            self.client.delete(f"{BASE_URL}/{account.id}").status_code, 204
        )

    def test_delete_missing_account(self):
        """Deleting an absent account is idempotent."""
        response = self.client.delete(f"{BASE_URL}/999999")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b"")

    def test_create_location(self):
        """The creation Location header points to the new account."""
        response = self.client.post(BASE_URL, json=AccountFactory().serialize())
        self.assertEqual(response.status_code, 201)
        location = response.headers["Location"]
        self.assertTrue(location.endswith(
            f"{BASE_URL}/{response.get_json()['id']}"
        ))
        saved = self.client.get(location)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.get_json(), response.get_json())

    def test_create_optional_fields(self):
        """Supply a default date and allow an omitted phone number."""
        from datetime import date
        data = AccountFactory().serialize()
        data.pop("date_joined")
        data.pop("phone_number")
        response = self.client.post(BASE_URL, json=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["date_joined"], date.today().isoformat())
        self.assertIsNone(response.get_json()["phone_number"])

    def test_create_invalid_date(self):
        """Reject a malformed account date."""
        data = AccountFactory().serialize()
        data["date_joined"] = "not-a-date"
        self.assertEqual(self.client.post(BASE_URL, json=data).status_code, 400)

    def test_create_non_object(self):
        """Reject JSON that is not an account object."""
        self.assertEqual(self.client.post(BASE_URL, json=[]).status_code, 400)

    def test_create_malformed_json(self):
        """Reject invalid JSON syntax."""
        response = self.client.post(
            BASE_URL, data="{bad", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_method_not_allowed(self):
        """Reject unsupported collection methods."""
        self.assertEqual(self.client.put(BASE_URL, json={}).status_code, 405)

    def test_server_error_response(self):
        """Return a JSON error when the database unexpectedly fails."""
        from unittest.mock import patch
        previous = app.config.get("PROPAGATE_EXCEPTIONS")
        app.config["PROPAGATE_EXCEPTIONS"] = False
        try:
            with patch("service.routes.Account.all", side_effect=RuntimeError("Database unavailable")):
                response = self.client.get(BASE_URL)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.get_json()["error"], "Internal Server Error")
        finally:
            app.config["PROPAGATE_EXCEPTIONS"] = previous

    def test_account_representation(self):
        """The model representation identifies the account."""
        account = self._create_accounts(1)[0]
        self.assertEqual(repr(account), f"<Account {account.name} id=[{account.id}]>")
