import pytest

from src.main import (
    Product,
    Customer,
    Admin,
    PaymentProcessor,
    ShippingService,
    OrderStatus,
    PaymentField,
    OrderItem,
    Order,
    Currency,
)


@pytest.fixture
def sample_products():
    return [
        Product(1, "Laptop", 1000.0, 5),
        Product(2, "Mouse", 25.0, 10),
        Product(3, "Keyboard", 75.0, 8),
    ]


@pytest.fixture
def sample_customer():
    return Customer(1, "John Doe", "john@example.com", "123 Main St")


@pytest.fixture
def sample_admin():
    return Admin(2, "Admin User", "admin@example.com", "full")


@pytest.fixture
def sample_order(sample_customer, sample_products):
    order = sample_customer.create_order()
    order.add_item(sample_products[0], 1)  # Laptop
    order.add_item(sample_products[1], 2)  # Mouse
    return order


@pytest.fixture
def payment_processor():
    return PaymentProcessor()


@pytest.fixture
def shipping_service():
    return ShippingService()


class TestProduct:
    def test_product_creation(self):
        product = Product(1, "Test Product", 100.0, 10)
        assert product.id == 1
        assert product.name == "Test Product"
        assert product.price == 100.0
        assert product.quantity == 10

    def test_reduce_stock_success(self, sample_products):
        product = sample_products[0]
        initial_quantity = product.quantity
        product.reduce_stock(2)
        assert product.quantity == initial_quantity - 2

    def test_reduce_stock_insufficient(self, sample_products):
        product = sample_products[0]
        with pytest.raises(ValueError, match="Not enough goods"):
            product.reduce_stock(100)

    def test_reduce_stock_negative(self, sample_products):
        product = sample_products[0]
        with pytest.raises(ValueError, match="The quantity must be positive"):
            product.reduce_stock(-1)

    def test_increase_stock(self, sample_products):
        product = sample_products[0]
        initial_quantity = product.quantity
        product.increase_stock(5)
        assert product.quantity == initial_quantity + 5

    def test_is_available(self, sample_products):
        product = sample_products[0]
        assert product.is_available(3) is True
        assert product.is_available(10) is False

    def test_string_representation(self, sample_products):
        product = sample_products[0]
        assert "Laptop" in str(product)
        assert "1000.0" in str(product)


class TestOrderItem:
    def test_order_item_creation(self, sample_products):
        product = sample_products[0]
        order_item = OrderItem(product, 2)
        assert order_item.product == product
        assert order_item.quantity == 2
        assert order_item.total_cost == 2000.0

    def test_order_item_insufficient_stock(self, sample_products):
        product = sample_products[0]
        with pytest.raises(ValueError, match="not available"):
            OrderItem(product, 100)

    def test_total_cost_calculation(self, sample_products):
        product = sample_products[1]  # Mouse: 25.0
        order_item = OrderItem(product, 3)
        assert order_item.total_cost == 75.0


class TestOrder:
    def test_order_creation(self, sample_customer):
        order = Order(1, sample_customer)
        assert order.order_id == 1
        assert order.customer == sample_customer
        assert order.status == OrderStatus.CREATED
        assert len(order) == 0
        assert order.total_cost == 0.0

    def test_add_item(self, sample_order, sample_products):
        assert len(sample_order) == 2
        assert sample_order.total_cost == 1050.0

    def test_add_duplicate_item(self, sample_order, sample_products):
        initial_quantity = sample_products[0].quantity
        sample_order.add_item(sample_products[0], 1)

        assert len(sample_order) == 2
        assert sample_order.total_cost == 2050.0
        assert sample_products[0].quantity == initial_quantity - 1

    def test_remove_item(self, sample_order, sample_products):
        initial_quantity = sample_products[0].quantity
        sample_order.remove_item(1)
        assert len(sample_order) == 1
        assert sample_products[0].quantity == initial_quantity + 1

    def test_remove_nonexistent_item(self, sample_order):
        with pytest.raises(ValueError, match="not found"):
            sample_order.remove_item(999)

    def test_pay_order(self, sample_order):
        sample_order.pay()
        assert sample_order.status == OrderStatus.PAID

    def test_pay_empty_order(self, sample_customer):
        order = Order(1, sample_customer)
        with pytest.raises(ValueError, match="empty order"):
            order.pay()

    def test_cancel_order(self, sample_order, sample_products):
        initial_quantities = {p.id: p.quantity for p in sample_products}
        sample_order.cancel()
        assert sample_order.status == OrderStatus.CANCELLED
        for product in sample_products:
            if product.id in initial_quantities:
                assert product.quantity >= initial_quantities[product.id]

    def test_modify_paid_order(self, sample_order):
        sample_order.pay()
        with pytest.raises(ValueError, match="cannot be changed"):
            sample_order.add_item(Product(4, "Tablet", 500.0, 3), 1)


class TestUsers:
    def test_user_creation(self):
        user = Customer(1, "Test User", "test@example.com", "124 Main St")
        assert user.user_id == 1
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.authenticate("default_password") is True
        assert user.authenticate("wrong_password") is False

    def test_customer_creation(self, sample_customer):
        assert sample_customer.user_id == 1
        assert sample_customer.name == "John Doe"
        assert sample_customer.address == "123 Main St"
        assert len(sample_customer.order_history) == 0

    def test_customer_order_management(self, sample_customer, sample_products):
        order = sample_customer.create_order()
        order.add_item(sample_products[0], 1)
        order.pay()
        sample_customer.add_to_history(order)

        assert len(sample_customer.order_history) == 1
        assert sample_customer.total_spent == 1000.0

    def test_admin_creation(self, sample_admin):
        assert sample_admin.user_id == 2
        assert sample_admin.access_level == "full"
        assert "Admin" in sample_admin.info

    def test_admin_add_product(self, sample_admin):
        products = []
        new_product = sample_admin.add_product(products, 10, "Monitor", 300.0, 5)

        assert len(products) == 1
        assert new_product.name == "Monitor"
        assert new_product.price == 300.0


class TestPaymentProcessor:
    def test_process_payment_success(self, sample_order, payment_processor):
        payment_details = {
            PaymentField.CARD_NUMBER: "1234567812345678",
            PaymentField.EXPIRY_DATE: "12/25",
            PaymentField.CVV: "123",
        }
        result = payment_processor.process_payment(sample_order, payment_details)
        assert result is True
        assert sample_order.status == OrderStatus.PAID

    def test_process_payment_invalid_details(self, sample_order, payment_processor):
        payment_details = {"card_number": "12345678"}  # Неполные данные
        result = payment_processor.process_payment(sample_order, payment_details)
        assert result is False
        assert sample_order.status == OrderStatus.CREATED

    def test_process_zero_amount_payment(self, sample_customer, payment_processor):
        order = Order(1, sample_customer)
        payment_details = {
            PaymentField.CARD_NUMBER: "1234567812345678",
            PaymentField.EXPIRY_DATE: "12/25",
            PaymentField.CVV: "123",
        }
        with pytest.raises(ValueError, match="must be positive"):
            payment_processor.process_payment(order, payment_details)

    def test_supported_currencies_initialization(self, payment_processor):
        assert payment_processor.is_currency_supported(Currency.USD)
        assert payment_processor.is_currency_supported(Currency.EUR)
        assert payment_processor.is_currency_supported(Currency.RUB)


class TestShippingService:
    def test_schedule_shipping_success(self, sample_order, shipping_service):
        sample_order.pay()
        tracking_number = shipping_service.schedule_shipping(sample_order, "123 Main St")

        assert sample_order.status == OrderStatus.SHIPPED
        assert tracking_number.startswith("TRK")
        assert sample_order.order_id in shipping_service.tracking_numbers

    def test_schedule_shipping_unpaid(self, sample_order, shipping_service):
        with pytest.raises(ValueError, match="Only paid orders"):
            shipping_service.schedule_shipping(sample_order, "123 Main St")

    def test_deliver_order_success(self, sample_order, shipping_service):
        sample_order.pay()
        shipping_service.schedule_shipping(sample_order, "123 Main St")
        shipping_service.deliver_order(sample_order)

        assert sample_order.status == OrderStatus.DELIVERED

    def test_deliver_undelivered_order(self, sample_order, shipping_service):
        sample_order.pay()
        with pytest.raises(ValueError, match="not yet been shipped"):
            shipping_service.deliver_order(sample_order)


class TestIntegration:
    def test_complete_order_flow(
        self, sample_customer, sample_products, payment_processor, shipping_service
    ):
        order = sample_customer.create_order()
        order.add_item(sample_products[0], 1)  # Laptop
        order.add_item(sample_products[1], 1)  # Mouse

        assert order.status == OrderStatus.CREATED
        assert len(order) == 2

        payment_details = {
            PaymentField.CARD_NUMBER: "1234567812345678",
            PaymentField.EXPIRY_DATE: "12/25",
            PaymentField.CVV: "123",
        }
        assert payment_processor.process_payment(order, payment_details) is True
        assert order.status == OrderStatus.PAID

        tracking_number = shipping_service.schedule_shipping(order, sample_customer.address)
        assert order.status == OrderStatus.SHIPPED
        assert tracking_number is not None

        shipping_service.deliver_order(order)
        assert order.status == OrderStatus.DELIVERED

        sample_customer.add_to_history(order)
        assert len(sample_customer.order_history) == 1
        assert sample_customer.total_spent == 1025.0  # 1000 + 25

    def test_order_cancellation_flow(self, sample_customer, sample_products):
        order = sample_customer.create_order()
        initial_quantity = sample_products[0].quantity
        order.add_item(sample_products[0], 1)

        assert sample_products[0].quantity == initial_quantity - 1

        order.cancel()
        assert order.status == OrderStatus.CANCELLED

        assert sample_products[0].quantity == initial_quantity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
