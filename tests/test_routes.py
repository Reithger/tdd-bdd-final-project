######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        # response = self.client.get(location)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new_product = response.get_json()
        # self.assertEqual(new_product["name"], test_product.name)
        # self.assertEqual(new_product["description"], test_product.description)
        # self.assertEqual(Decimal(new_product["price"]), test_product.price)
        # self.assertEqual(new_product["available"], test_product.available)
        # self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #

    def test_read_a_product(self):
        """ It should retrieve a product by its ID """
        # Set up initial data in the database
        test_product = self._create_products()[0]
        # Query database for id of our test product
        response = self.client.get(BASE_URL + "/" + str(test_product.id))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)
        # Test failure case of querying for non-existent product id
        response = self.client.get(BASE_URL + "/999999")
        self.assertEqual(response.status_code, 404)

    def test_update_a_product(self):
        """ It should update a product's contents by its ID reference """
        # Set up initial data in the database
        test_product = ProductFactory()
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, 201)
        new_product = response.get_json()
        # Update the product data we have locally for sending to the server
        new_description = "New description"
        new_product["description"] = new_description
        # Make the put call to update the database
        response = self.client.put(BASE_URL + "/" + str(new_product["id"]), json=new_product)
        self.assertEqual(response.status_code, 200)
        newest_product = response.get_json()
        self.assertEqual(newest_product["description"], new_description)
        # Test failure case of updating non-existent product
        response = self.client.put(BASE_URL + "/99999", json=new_product)
        self.assertEqual(response.status_code, 404)

    def test_delete_product(self):
        """ It should remove a product from the database specified by its ID """
        # Set up initial data in the database
        test_product = self._create_products()[0]
        # Check that the product is there
        response = self.client.get(BASE_URL + "/" + str(test_product.id))
        self.assertEqual(response.status_code, 200)
        # Remove the product
        response = self.client.delete(BASE_URL + "/" + str(test_product.id))
        self.assertEqual(response.status_code, 204)
        # Check that the product is not there
        response = self.client.get(BASE_URL + "/" + str(test_product.id))
        self.assertEqual(response.status_code, 404)

        # Setup numerous data
        test_products = self._create_products(10)
        self.assertEqual(10, self.get_product_count())
        # Delete one product
        response = self.client.delete(BASE_URL + "/" + str(test_products[0].id))
        self.assertEqual(response.status_code, 204)
        # Check that no data is returned and that the database has removed a product
        self.assertEqual(len(response.get_data()), 0)
        self.assertEqual(9, self.get_product_count())

    def test_list_all_products(self):
        """ It should Get a list of products """
        # Setup products in the database
        self._create_products(5)
        # Request the list of products from the database
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, 200)
        # Check that the list of products has the correct length
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_list_by_name(self):
        """ It should get a list of products with a specific name """
        # Setup products in the database with local references
        products = self._create_products(10)
        # Get a default name to check in the database, count its occurences in case of dupes
        name_ref = products[0].name
        count = len([prod for prod in products if prod.name == name_ref])
        # Query the database for all products that have a particular name
        response = self.client.get(BASE_URL, query_string=f"name={quote_plus(name_ref)}")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        # Ensure that the returned data has as many product entries as was generated with that name
        self.assertEqual(count, len(data))
        # Ensure all the returned data has the correct name
        for prod in data:
            self.assertEqual(name_ref, prod["name"])

    def test_list_by_category(self):
        """ It should get a list of products with a specific category """
        # Setup products in the database with local references
        products = self._create_products(10)
        # Get reference category from one of the products and count its occurence
        category_ref = products[0].category
        count = len([prod for prod in products if prod.category == category_ref])
        # Make the query to the database using our category and ensure 200 status code
        response = self.client.get(BASE_URL, query_string=f"category={str(category_ref.name)}")
        self.assertEqual(response.status_code, 200)
        # Acquire the data and test it returned the correct amount of products
        data = response.get_json()
        self.assertEqual(count, len(data))
        # Ensure all the returned data has the correct category
        for prod in data:
            self.assertEqual(category_ref.name, prod["category"])

    def test_list_by_availability(self):
        """ It should get a list of products with a specific availability """
        # Setup products in the database with local references
        products = self._create_products(10)
        # Get reference category from one of the products and count its occurence
        availability_ref = products[0].available
        use = "True"
        if availability_ref is False:
            use = "False"
        count = len([prod for prod in products if prod.available == availability_ref])
        # Make the query to the database using our category and ensure 200 status code
        response = self.client.get(BASE_URL, query_string=f"available={use}")
        self.assertEqual(response.status_code, 200)
        # Acquire the data and test it returned the correct amount of products
        data = response.get_json()
        self.assertEqual(count, len(data))
        # Ensure all the returned data has the correct category
        for prod in data:
            self.assertEqual(availability_ref, prod["available"])

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
