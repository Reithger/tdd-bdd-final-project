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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    #
    # ADD YOUR TEST CASES HERE
    #

    def test_read_a_product(self):
        """ Test to verify that we can retrieve a Product from the system via its ID """
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        copy = Product.find(product.id)
        self.assertEqual(product.id, copy.id)
        self.assertEqual(product.name, copy.name)
        self.assertEqual(product.description, copy.description)
        self.assertEqual(product.price, copy.price)
        self.assertEqual(product.available, copy.available)
        self.assertEqual(product.category, copy.category)

    def test_update_a_product(self):
        """ Test to verify that updating the details of a product works correctly """
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertNotEqual(None, product.id)
        test_descr = "New test description"
        product.description = test_descr
        original_id = product.id
        product.update()
        self.assertEqual(product.id, original_id)
        self.assertEqual(product.description, test_descr)
        prods = Product.all()
        self.assertEqual(1, len(prods))
        self.assertEqual(prods[0].id, product.id)
        self.assertEqual(prods[0].description, product.description)
        product.id = None
        with self.assertRaises(DataValidationError):
            product.update()

    def test_delete_a_product(self):
        """ Test to verify that deleting a product works """
        product = ProductFactory()
        product.ID = None
        prods = Product.all()
        self.assertEqual(0, len(prods))
        product.create()
        prods = Product.all()
        self.assertEqual(1, len(prods))
        product.delete()
        prods = Product.all()
        self.assertEqual(0, len(prods))

    def test_list_all_products(self):
        """ Test to verify if the Product class listing functionality works """
        prods = Product.all()
        self.assertEqual(0, len(prods))
        for i in range(5):
            product = ProductFactory()
            product.create()
        prods = Product.all()
        self.assertEqual(5, len(prods))

    def test_search_product_by_name(self):
        """ Test to check that searching a product by name works """
        add_products = ProductFactory.create_batch(5)
        for product in add_products:
            product.create()
        prods = Product.all()
        name = prods[0].name
        name_prods = Product.find_by_name(name)
        count = len([prod for prod in add_products if prod.name == name])
        for prod in name_prods:
            self.assertEqual(name, prod.name)
        self.assertEqual(count, name_prods.count())

    def test_find_by_availability(self):
        """ Test to verify that Product can find by availability correctly """
        add_products = ProductFactory.create_batch(10)
        for product in add_products:
            product.create()
        prods = Product.all()
        available = prods[0].available
        count = len([prod for prod in add_products if prod.available == available])
        prods = Product.find_by_availability(available)
        self.assertEqual(count, prods.count())
        for product in prods:
            self.assertEqual(product.available, available)
        
    def test_find_by_category(self):
        """ Test to verify that find_by_category correctly works """
        add_products = ProductFactory.create_batch(10)
        for product in add_products:
            product.create()
        category = add_products[0].category
        count = len([prod for prod in add_products if category == prod.category])
        prods = Product.find_by_category(category)
        self.assertEqual(count, prods.count())
        for product in prods:
            self.assertEqual(category, product.category)

    def test_find_by_price(self):
        """ Test to verify that find_by_price correctly works """
        add_products = ProductFactory.create_batch(10)
        for product in add_products:
            product.create()
        for product in add_products:
            find_product = Product.find_by_price(product.price)
            found = False
            for ot_prod in find_product:
                self.assertEqual(ot_prod.price, product.price)
                if(ot_prod.id == product.id):
                    found = True
            self.assertTrue(found)
        str_product = ProductFactory()
        str_product.price = 99999.99
        str_product.create()
        self.assertEqual(str_product.id, Product.find_by_price("99999.99")[0].id)